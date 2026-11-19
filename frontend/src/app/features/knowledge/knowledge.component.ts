import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { OpsService } from '../../core/services/ops.service';
import { KnowledgeDocument, PolicyCitation } from '../../core/models';

@Component({
  selector: 'app-knowledge',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="p-6 space-y-4 max-w-7xl mx-auto">
      <!-- Page Header -->
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[var(--border-subtle)]">
        <div>
          <div class="flex items-center gap-2">
            <h1 class="text-xl font-semibold tracking-tight text-primary">Enterprise Knowledge Base (RAG)</h1>
            <span class="badge badge-brand font-mono text-[10px]">CHROMADB ACTIVE</span>
          </div>
          <p class="text-xs text-secondary mt-0.5">Vector retrieval engine indexing enterprise operational policies for factual grounding</p>
        </div>
        <div class="flex items-center gap-2">
          <button class="btn btn-secondary btn-xs" (click)="loadDocs()">
            <svg width="14" height="14" class="w-3.5 h-3.5 text-muted" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/><path d="M16 21h5v-5"/></svg>
            <span>Refresh</span>
          </button>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-12 gap-4">
        <!-- Left Column: Document Ingestion & Corpus Index (7 cols) -->
        <div class="lg:col-span-7 space-y-4">
          <!-- Ingestion Station -->
          <div class="op-card space-y-3">
            <div class="panel-header mb-0 pb-2">
              <div class="panel-title">
                <svg width="16" height="16" class="w-4 h-4 text-brand" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                <span>Ingest Operational Policy</span>
              </div>
              <span class="text-xs text-muted font-mono">PDF & TXT Supported</span>
            </div>
            <p class="text-xs text-secondary">
              Upload operational policies or logistics manuals. The pipeline chunks documents, computes 384-dimensional dense vectors, and syncs both SQL and ChromaDB vector stores.
            </p>
            <div class="flex items-center gap-2 pt-1">
              <input type="file" #fileInput (change)="onFileSelected($event)" accept=".pdf,.txt,.md" class="hidden" />
              <button class="btn btn-primary btn-xs" (click)="fileInput.click()" [disabled]="isUploading()">
                <svg width="14" height="14" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                <span>{{ isUploading() ? 'Vectorizing Document...' : 'Select Document File' }}</span>
              </button>
              <span class="text-xs text-muted font-mono" *ngIf="uploadStatus()">{{ uploadStatus() }}</span>
            </div>
          </div>

          <!-- Document List Table -->
          <div class="op-card">
            <div class="panel-header">
              <div class="panel-title">
                <svg width="16" height="16" class="w-4 h-4 text-secondary" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"/></svg>
                <span>Indexed Policy Corpus ({{ documents().length }})</span>
              </div>
              <span class="text-xs text-brand font-mono">{{ totalVectors() }} Total Vectors in ChromaDB</span>
            </div>

            <div class="op-table-container">
              <table class="op-table">
                <thead>
                  <tr>
                    <th>Filename</th>
                    <th>Type</th>
                    <th>Chunks</th>
                    <th>Size</th>
                    <th class="text-right">Action</th>
                  </tr>
                </thead>
                <tbody>
                  <tr *ngFor="let doc of documents()" class="hover:bg-[var(--bg-hover)] transition">
                    <td class="font-medium text-primary text-xs flex items-center gap-2">
                      <svg width="14" height="14" class="w-3.5 h-3.5 text-muted flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                      <span class="truncate max-w-[200px]" [title]="doc.filename">{{ doc.filename }}</span>
                    </td>
                    <td class="font-mono text-muted text-[11px] uppercase">{{ doc.document_type }}</td>
                    <td class="font-mono text-brand font-semibold text-xs">{{ doc.chunk_count }}</td>
                    <td class="font-mono text-muted text-[11px]">{{ (doc.file_size / 1024) | number:'1.1-1' }} KB</td>
                    <td class="text-right">
                      <button class="btn btn-ghost btn-xs text-muted hover:text-rose-400" (click)="deleteDoc(doc.id)" title="Delete policy and purge ChromaDB vectors">
                        <svg width="14" height="14" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Right Column: Live Semantic Vector Search Tester (5 cols) -->
        <div class="lg:col-span-5 op-card space-y-3 flex flex-col">
          <div class="panel-header mb-0 pb-2">
            <div class="panel-title">
              <svg width="16" height="16" class="w-4 h-4 text-brand" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
              <span>Live Vector Search Tester</span>
            </div>
            <span class="text-xs text-muted font-mono">Cosine Similarity</span>
          </div>

          <div class="space-y-2">
            <label class="op-label">Query Policy Corpus</label>
            <div class="flex gap-2">
              <input
                type="text"
                [(ngModel)]="searchQuery"
                (keydown.enter)="search()"
                placeholder="e.g. Can I return opened electronics after 20 days?"
                class="op-input text-xs"
              />
              <button class="btn btn-primary btn-xs" (click)="search()" [disabled]="isSearching() || !searchQuery.trim()">
                Search
              </button>
            </div>
          </div>

          <!-- Quick Test Prompts -->
          <div class="flex flex-wrap gap-1.5 pt-1">
            <button 
              class="px-2 py-0.5 rounded text-[10px] bg-[var(--bg-elevated)] border border-[var(--border-default)] text-secondary hover:text-primary transition"
              (click)="quickSearch('What is the return window for electronics?')"
            >
              Return Window
            </button>
            <button 
              class="px-2 py-0.5 rounded text-[10px] bg-[var(--bg-elevated)] border border-[var(--border-default)] text-secondary hover:text-primary transition"
              (click)="quickSearch('What happens if delivery is delayed by blizzard?')"
            >
              Weather Delay SLA
            </button>
            <button 
              class="px-2 py-0.5 rounded text-[10px] bg-[var(--bg-elevated)] border border-[var(--border-default)] text-secondary hover:text-primary transition"
              (click)="quickSearch('Orphan charge without order confirmation')"
            >
              Payment Discrepancy
            </button>
          </div>

          <!-- Search Results List -->
          <div class="space-y-2 flex-1 overflow-y-auto max-h-[420px] pt-2">
            <div *ngIf="isSearching()" class="py-12 text-center text-xs text-muted font-mono animate-pulse">
              Computing cosine distance across 384-dim policy vectors...
            </div>

            <div *ngIf="!isSearching() && searchResults().length === 0" class="py-12 text-center text-xs text-muted">
              Enter a query to inspect live ChromaDB semantic retrieval chunks.
            </div>

            <div *ngFor="let cit of searchResults()" class="p-3 rounded bg-[var(--bg-canvas)] border border-[var(--border-default)] text-xs space-y-1.5">
              <div class="flex items-center justify-between text-[11px]">
                <span class="font-mono text-secondary truncate max-w-[200px]" [title]="cit.source_document">{{ cit.source_document }}</span>
                <span class="badge badge-brand font-mono text-[10px]">{{ (cit.relevance_score * 100) | number:'1.0-0' }}% Match</span>
              </div>
              <div class="font-semibold text-primary text-xs">{{ cit.section }}</div>
              <p class="text-secondary text-[11px] leading-relaxed italic bg-[var(--bg-elevated)] p-2 rounded">
                "{{ cit.snippet }}"
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    :host {
      display: block;
    }
  `]
})
export class KnowledgeComponent implements OnInit {
  private readonly ops = inject(OpsService);

  readonly documents = signal<KnowledgeDocument[]>([]);
  readonly searchResults = signal<PolicyCitation[]>([]);
  readonly isUploading = signal(false);
  readonly isSearching = signal(false);
  readonly uploadStatus = signal<string | null>(null);

  searchQuery = 'What is the return window for defective items?';

  ngOnInit(): void {
    this.loadDocs();
  }

  loadDocs(): void {
    this.ops.listKnowledgeDocuments().subscribe({
      next: (res) => this.documents.set(res),
      error: (err) => console.error('Failed to load documents', err)
    });
  }

  totalVectors(): number {
    return this.documents().reduce((acc, d) => acc + (d.chunk_count || 0), 0);
  }

  onFileSelected(event: any): void {
    const file = event.target.files[0];
    if (!file) return;

    this.isUploading.set(true);
    this.uploadStatus.set(`Uploading & chunking ${file.name}...`);

    this.ops.uploadDocument(file).subscribe({
      next: (doc) => {
        this.isUploading.set(false);
        this.uploadStatus.set(`Successfully indexed: ${doc.filename} (${doc.chunk_count} chunks)`);
        this.loadDocs();
      },
      error: (err) => {
        console.error('Upload failed', err);
        this.isUploading.set(false);
        this.uploadStatus.set('Upload failed: ' + (err.error?.detail || err.message));
      }
    });
  }

  deleteDoc(id: number): void {
    if (!confirm('Are you sure you want to purge this document and all associated ChromaDB vectors?')) return;

    this.ops.deleteKnowledgeDocument(id).subscribe({
      next: () => this.loadDocs(),
      error: (err) => console.error('Delete failed', err)
    });
  }

  quickSearch(q: string): void {
    this.searchQuery = q;
    this.search();
  }

  search(): void {
    if (!this.searchQuery.trim()) return;

    this.isSearching.set(true);
    this.ops.searchKnowledge(this.searchQuery, 3).subscribe({
      next: (res) => {
        this.searchResults.set(res.citations || []);
        this.isSearching.set(false);
      },
      error: (err) => {
        console.error('Search failed', err);
        this.isSearching.set(false);
      }
    });
  }
}
