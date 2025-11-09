# Chrome Extension MVP for Second Brain

**Version:** 1.0  
**Date:** January 27, 2025  
**Status:** AUTHORITATIVE SPECIFICATION  
**Purpose:** Complete specification for Chrome extension that captures ChatGPT and Claude conversations with modular architecture for future chat platforms

---

## Table of Contents

1. [Extension Overview & Architecture](#1-extension-overview--architecture)
2. [Platform-Specific Parsers (Modular Design)](#2-platform-specific-parsers-modular-design)
3. [Core Features Specification](#3-core-features-specification)
4. [UI Components & User Experience](#4-ui-components--user-experience)
5. [API Integration](#5-api-integration)
6. [Offline Queue & Sync](#6-offline-queue--sync)
7. [Action Item Extraction (Client-Side Preview)](#7-action-item-extraction-client-side-preview)
8. [Todo/Task Tracking](#8-todotask-tracking)
9. [Configuration & Settings](#9-configuration--settings)
10. [Testing & Quality Assurance](#10-testing--quality-assurance)

---

## 1. Extension Overview & Architecture

### 1.1 Purpose and Goals

**Primary Purpose:**
Capture conversations from ChatGPT and Claude AI chat platforms and import them into Second Brain for processing, action item extraction, and knowledge management.

**Key Goals:**
- Real-time conversation monitoring and one-click capture
- Modular architecture for easy addition of new chat platforms
- Client-side action item extraction preview
- In-extension todo/task tracking
- Offline queue management with automatic sync
- Seamless integration with Second Brain API

**Non-Goals (MVP):**
- Full conversation editing within extension
- Direct note editing in Second Brain
- Multi-user collaboration
- Cloud sync (uses Second Brain API as single source of truth)

### 1.2 Technology Stack

**Core Technologies:**
- **Manifest Version**: V3 (required for Chrome Web Store)
- **Language**: TypeScript (strict mode, ES2020+)
- **UI Framework**: Vanilla JavaScript with Shadow DOM (lightweight, no framework dependencies)
- **Build Tool**: Webpack or Vite
- **Testing**: Jest + Puppeteer for E2E
- **Storage**: chrome.storage.local (for offline queue)

**Dependencies (Minimal):**
- No external UI frameworks (keep bundle size small)
- UUID library for idempotency keys
- Date-fns for date formatting (lightweight)

### 1.3 File Structure and Organization

```
second-brain-extension/
├── manifest.json                 # Extension manifest (V3)
├── package.json
├── tsconfig.json
├── webpack.config.js
├── src/
│   ├── background/
│   │   ├── service-worker.ts     # Background service worker
│   │   ├── api-client.ts         # Second Brain API client
│   │   ├── queue-manager.ts      # Offline queue management
│   │   └── sync-manager.ts       # Background sync logic
│   ├── content/
│   │   ├── content-script.ts     # Main content script
│   │   ├── ui-injector.ts        # UI component injection
│   │   └── parsers/
│   │       ├── base-parser.ts    # Base parser interface
│   │       ├── chatgpt-parser.ts # ChatGPT parser
│   │       ├── claude-parser.ts  # Claude parser
│   │       └── parser-registry.ts # Parser registration
│   ├── popup/
│   │   ├── popup.html
│   │   ├── popup.ts              # Popup UI logic
│   │   └── settings.ts            # Settings management
│   ├── shared/
│   │   ├── types.ts              # TypeScript interfaces
│   │   ├── constants.ts          # Constants and config
│   │   ├── utils.ts              # Utility functions
│   │   └── action-extractor.ts   # Client-side action extraction
│   └── styles/
│       ├── content.css           # Content script styles
│       └── popup.css              # Popup styles
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── README.md
```

### 1.4 Extension Lifecycle

**Installation:**
1. User installs extension from Chrome Web Store
2. Extension requests permissions (activeTab, storage)
3. User configures API endpoint and API key in settings
4. Extension validates API connection

**Runtime:**
1. Content script injects on ChatGPT/Claude pages
2. Parser detects platform and initializes
3. UI components (capture button, todo sidebar) injected
4. Real-time monitoring watches for conversation changes
5. User clicks capture → extracts conversation → sends to API
6. Background sync handles offline queue

**Update:**
- Extension auto-updates via Chrome Web Store
- Settings and queue data preserved
- Parser selectors updated if DOM changes

---

## 2. Platform-Specific Parsers (Modular Design)

### 2.1 Base Parser Interface

**TypeScript Interface:**
```typescript
interface ChatPlatformParser {
  /** Unique platform identifier */
  platformId: 'chatgpt' | 'claude' | 'other';
  
  /** Human-readable platform name */
  platformName: string;
  
  /** Check if current page matches this platform */
  detect(): boolean;
  
  /** Extract full conversation from page */
  extractConversation(): Conversation | null;
  
  /** Extract conversation title */
  extractTitle(): string | null;
  
  /** Extract all messages from conversation */
  extractMessages(): Message[];
  
  /** Get unique conversation ID from page */
  getConversationId(): string | null;
  
  /** Get model name if available (e.g., "gpt-4", "claude-3-opus") */
  getModel(): string | null;
  
  /** Watch for conversation changes and call callback */
  watchForChanges(callback: (conversation: Conversation) => void): void;
  
  /** Stop watching for changes */
  stopWatching(): void;
  
  /** Check if conversation has new messages since last check */
  hasNewMessages(lastMessageCount: number): boolean;
}
```

**Base Abstract Class:**
```typescript
abstract class BaseParser implements ChatPlatformParser {
  abstract platformId: 'chatgpt' | 'claude' | 'other';
  abstract platformName: string;
  
  protected observer: MutationObserver | null = null;
  protected lastMessageCount: number = 0;
  
  abstract detect(): boolean;
  abstract extractConversation(): Conversation | null;
  abstract extractTitle(): string | null;
  abstract extractMessages(): Message[];
  abstract getConversationId(): string | null;
  abstract getModel(): string | null;
  
  watchForChanges(callback: (conversation: Conversation) => void): void {
    // Default implementation using MutationObserver
    const targetNode = document.body;
    const config = { childList: true, subtree: true };
    
    this.observer = new MutationObserver(() => {
      const conversation = this.extractConversation();
      if (conversation && conversation.messages.length > this.lastMessageCount) {
        this.lastMessageCount = conversation.messages.length;
        callback(conversation);
      }
    });
    
    this.observer.observe(targetNode, config);
  }
  
  stopWatching(): void {
    if (this.observer) {
      this.observer.disconnect();
      this.observer = null;
    }
  }
  
  hasNewMessages(lastMessageCount: number): boolean {
    const currentMessages = this.extractMessages();
    return currentMessages.length > lastMessageCount;
  }
}
```

### 2.2 ChatGPT Parser Implementation

**DOM Selectors (Current as of 2024):**
```typescript
class ChatGPTParser extends BaseParser {
  platformId = 'chatgpt' as const;
  platformName = 'ChatGPT';
  
  // DOM Selectors (update if ChatGPT changes structure)
  private readonly SELECTORS = {
    // Conversation container
    conversationContainer: 'main > div:first-child',
    
    // Title (in sidebar or header)
    title: '[data-testid="conversation-title"]',
    titleInput: 'input[placeholder*="Untitled"]',
    
    // Messages container
    messagesContainer: '[data-testid="conversation-turn"]',
    
    // Individual message
    message: '[data-testid="conversation-turn"]',
    userMessage: '[data-message-author-role="user"]',
    assistantMessage: '[data-message-author-role="assistant"]',
    
    // Message content
    messageContent: '[data-message-content]',
    messageText: 'div[class*="markdown"]',
    
    // Conversation ID (from URL or data attribute)
    conversationId: () => {
      // Extract from URL: https://chat.openai.com/c/{id}
      const match = window.location.pathname.match(/\/c\/([a-f0-9-]+)/);
      return match ? match[1] : null;
    }
  };
  
  detect(): boolean {
    return window.location.hostname.includes('chat.openai.com') ||
           window.location.hostname.includes('chatgpt.com');
  }
  
  extractTitle(): string | null {
    // Try title input first
    const titleInput = document.querySelector(this.SELECTORS.titleInput) as HTMLInputElement;
    if (titleInput && titleInput.value) {
      return titleInput.value.trim();
    }
    
    // Try title element
    const titleEl = document.querySelector(this.SELECTORS.title);
    if (titleEl) {
      return titleEl.textContent?.trim() || null;
    }
    
    // Fallback: use first user message or "Untitled"
    const firstUserMessage = document.querySelector(this.SELECTORS.userMessage);
    if (firstUserMessage) {
      const text = firstUserMessage.textContent?.trim() || '';
      return text.substring(0, 50) || 'Untitled Conversation';
    }
    
    return 'Untitled Conversation';
  }
  
  extractMessages(): Message[] {
    const messages: Message[] = [];
    const messageElements = document.querySelectorAll(this.SELECTORS.message);
    
    messageElements.forEach((element, index) => {
      const role = element.hasAttribute('data-message-author-role') 
        ? element.getAttribute('data-message-author-role') 
        : (element.querySelector(this.SELECTORS.userMessage) ? 'user' : 'assistant');
      
      const contentEl = element.querySelector(this.SELECTORS.messageText) || 
                        element.querySelector(this.SELECTORS.messageContent);
      
      if (!contentEl) return;
      
      const content = contentEl.textContent?.trim() || '';
      if (!content) return;
      
      // Extract timestamp if available
      const timestampEl = element.querySelector('time');
      const timestamp = timestampEl?.getAttribute('datetime') || 
                       new Date().toISOString();
      
      messages.push({
        role: role === 'user' ? 'user' : 'assistant',
        content: content,
        timestamp: timestamp,
        metadata: {
          index: index,
          elementId: element.id || `msg-${index}`
        }
      });
    });
    
    return messages;
  }
  
  getConversationId(): string | null {
    return this.SELECTORS.conversationId();
  }
  
  getModel(): string | null {
    // ChatGPT model is often in settings or first message metadata
    // Look for model indicator in UI
    const modelIndicator = document.querySelector('[data-model]');
    if (modelIndicator) {
      return modelIndicator.getAttribute('data-model');
    }
    
    // Check URL params or localStorage
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('model') || 'gpt-4'; // Default assumption
  }
  
  extractConversation(): Conversation | null {
    if (!this.detect()) return null;
    
    const id = this.getConversationId();
    const title = this.extractTitle();
    const messages = this.extractMessages();
    const model = this.getModel();
    
    if (!id || !messages.length) return null;
    
    return {
      id: id,
      title: title || 'Untitled Conversation',
      platform: 'chatgpt',
      messages: messages,
      metadata: {
        url: window.location.href,
        capturedAt: new Date().toISOString(),
        model: model || undefined,
        conversationDate: this.extractConversationDate()
      }
    };
  }
  
  private extractConversationDate(): string | null {
    // Try to find date in sidebar or message timestamps
    const dateEl = document.querySelector('[data-date]');
    if (dateEl) {
      return dateEl.getAttribute('data-date');
    }
    return null;
  }
}
```

### 2.3 Claude Parser Implementation

**DOM Selectors (Current as of 2024):**
```typescript
class ClaudeParser extends BaseParser {
  platformId = 'claude' as const;
  platformName = 'Claude';
  
  private readonly SELECTORS = {
    // Conversation container
    conversationContainer: 'main, [data-conversation]',
    
    // Title
    title: 'h1, [data-title]',
    titleInput: 'input[aria-label*="title"], input[placeholder*="title"]',
    
    // Messages
    messagesContainer: '[data-message], .message',
    message: '[data-message], .message',
    userMessage: '[data-role="user"], .message-user',
    assistantMessage: '[data-role="assistant"], .message-assistant',
    
    // Message content
    messageContent: '[data-content], .message-content',
    messageText: '.message-text, [data-text]',
    
    // Conversation ID (from URL)
    conversationId: () => {
      // Claude URL pattern: https://claude.ai/chat/{id}
      const match = window.location.pathname.match(/\/chat\/([a-f0-9-]+)/);
      return match ? match[1] : window.location.pathname.split('/').pop() || null;
    }
  };
  
  detect(): boolean {
    return window.location.hostname.includes('claude.ai');
  }
  
  extractTitle(): string | null {
    const titleInput = document.querySelector(this.SELECTORS.titleInput) as HTMLInputElement;
    if (titleInput && titleInput.value) {
      return titleInput.value.trim();
    }
    
    const titleEl = document.querySelector(this.SELECTORS.title);
    if (titleEl) {
      return titleEl.textContent?.trim() || null;
    }
    
    return 'Untitled Conversation';
  }
  
  extractMessages(): Message[] {
    const messages: Message[] = [];
    const messageElements = document.querySelectorAll(this.SELECTORS.message);
    
    messageElements.forEach((element, index) => {
      const isUser = element.matches(this.SELECTORS.userMessage) ||
                    element.hasAttribute('data-role') && 
                    element.getAttribute('data-role') === 'user';
      
      const contentEl = element.querySelector(this.SELECTORS.messageText) ||
                       element.querySelector(this.SELECTORS.messageContent) ||
                       element;
      
      const content = contentEl.textContent?.trim() || '';
      if (!content) return;
      
      const timestamp = element.getAttribute('data-timestamp') ||
                       element.querySelector('time')?.getAttribute('datetime') ||
                       new Date().toISOString();
      
      messages.push({
        role: isUser ? 'user' : 'assistant',
        content: content,
        timestamp: timestamp,
        metadata: {
          index: index,
          elementId: element.id || `msg-${index}`
        }
      });
    });
    
    return messages;
  }
  
  getConversationId(): string | null {
    return this.SELECTORS.conversationId();
  }
  
  getModel(): string | null {
    // Claude model in settings or UI indicator
    const modelEl = document.querySelector('[data-model]');
    return modelEl?.getAttribute('data-model') || 'claude-3-opus';
  }
  
  extractConversation(): Conversation | null {
    if (!this.detect()) return null;
    
    const id = this.getConversationId();
    const title = this.extractTitle();
    const messages = this.extractMessages();
    const model = this.getModel();
    
    if (!id || !messages.length) return null;
    
    return {
      id: id,
      title: title || 'Untitled Conversation',
      platform: 'claude',
      messages: messages,
      metadata: {
        url: window.location.href,
        capturedAt: new Date().toISOString(),
        model: model || undefined,
        conversationDate: this.extractConversationDate()
      }
    };
  }
  
  private extractConversationDate(): string | null {
    const dateEl = document.querySelector('[data-date], time');
    return dateEl?.getAttribute('datetime') || dateEl?.getAttribute('data-date') || null;
  }
}
```

### 2.4 Parser Registration System

**Parser Registry:**
```typescript
class ParserRegistry {
  private parsers: Map<string, new () => BaseParser> = new Map();
  
  register(parserClass: new () => BaseParser): void {
    const instance = new parserClass();
    this.parsers.set(instance.platformId, parserClass);
  }
  
  detectParser(): BaseParser | null {
    for (const ParserClass of this.parsers.values()) {
      const parser = new ParserClass();
      if (parser.detect()) {
        return parser;
      }
    }
    return null;
  }
  
  getParser(platformId: string): BaseParser | null {
    const ParserClass = this.parsers.get(platformId);
    if (!ParserClass) return null;
    return new ParserClass();
  }
}

// Initialize registry
const parserRegistry = new ParserRegistry();
parserRegistry.register(ChatGPTParser);
parserRegistry.register(ClaudeParser);

// Future: parserRegistry.register(PerplexityParser);
// Future: parserRegistry.register(GeminiParser);
```

### 2.5 Conversation Data Structure

**Standardized Format:**
```typescript
interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string; // ISO 8601 format
  metadata?: {
    index?: number;
    elementId?: string;
    [key: string]: any;
  };
}

interface Conversation {
  id: string;                    // Unique conversation ID from platform
  title: string;                 // Conversation title
  platform: 'chatgpt' | 'claude' | 'other';
  messages: Message[];           // All messages in conversation
  metadata: {
    url: string;                 // Page URL when captured
    capturedAt: string;          // ISO 8601 timestamp
    model?: string;              // AI model used (e.g., "gpt-4", "claude-3-opus")
    conversationDate?: string;   // Original conversation date if available
    selectedMessages?: number[]; // Indices of selected messages (if selective capture)
  };
}
```

---

## 3. Core Features Specification

### 3.1 Real-Time Conversation Monitoring

**Implementation:**
- Parser watches for DOM changes using MutationObserver
- Detects new messages added to conversation
- Updates conversation state in memory
- Triggers UI updates (message count, capture button state)

**Monitoring Strategy:**
```typescript
class ConversationMonitor {
  private parser: BaseParser | null = null;
  private currentConversation: Conversation | null = null;
  private lastMessageCount: number = 0;
  private onChangeCallbacks: Array<(conv: Conversation) => void> = [];
  
  startMonitoring(parser: BaseParser): void {
    this.parser = parser;
    this.lastMessageCount = 0;
    
    parser.watchForChanges((conversation) => {
      this.currentConversation = conversation;
      this.onChangeCallbacks.forEach(cb => cb(conversation));
      this.updateUI(conversation);
    });
    
    // Initial extraction
    const initial = parser.extractConversation();
    if (initial) {
      this.currentConversation = initial;
      this.lastMessageCount = initial.messages.length;
    }
  }
  
  stopMonitoring(): void {
    if (this.parser) {
      this.parser.stopWatching();
    }
  }
  
  onConversationChange(callback: (conv: Conversation) => void): void {
    this.onChangeCallbacks.push(callback);
  }
  
  getCurrentConversation(): Conversation | null {
    return this.currentConversation;
  }
  
  hasNewMessages(): boolean {
    if (!this.parser || !this.currentConversation) return false;
    return this.parser.hasNewMessages(this.lastMessageCount);
  }
}
```

### 3.2 One-Click Capture Button

**Button Placement:**
- Floating button in top-right corner of chat interface
- Sticky position (stays visible when scrolling)
- Platform-specific positioning to avoid UI conflicts

**Button States:**
- **Default**: "Capture to Second Brain" (gray)
- **Hover**: Highlighted (blue)
- **Processing**: "Capturing..." with spinner
- **Success**: "Captured!" with checkmark (2 seconds)
- **Error**: "Failed" with error icon (5 seconds)

**Button Implementation:**
```typescript
class CaptureButton {
  private button: HTMLButtonElement;
  private state: 'idle' | 'processing' | 'success' | 'error' = 'idle';
  
  constructor() {
    this.button = this.createButton();
    this.injectButton();
  }
  
  private createButton(): HTMLButtonElement {
    const button = document.createElement('button');
    button.id = 'sb-capture-btn';
    button.className = 'sb-capture-button';
    button.textContent = 'Capture to Second Brain';
    button.addEventListener('click', () => this.handleClick());
    return button;
  }
  
  private injectButton(): void {
    // Inject into page with Shadow DOM for style isolation
    const container = document.createElement('div');
    container.id = 'sb-extension-container';
    const shadow = container.attachShadow({ mode: 'closed' });
    
    // Inject styles
    const style = document.createElement('style');
    style.textContent = this.getButtonStyles();
    shadow.appendChild(style);
    shadow.appendChild(this.button);
    
    document.body.appendChild(container);
  }
  
  private async handleClick(): Promise<void> {
    if (this.state === 'processing') return;
    
    this.setState('processing');
    
    try {
      const conversation = conversationMonitor.getCurrentConversation();
      if (!conversation) {
        throw new Error('No conversation found');
      }
      
      await apiClient.importConversation(conversation);
      this.setState('success');
      
      // Reset after 2 seconds
      setTimeout(() => this.setState('idle'), 2000);
    } catch (error) {
      this.setState('error');
      this.showError(error);
      setTimeout(() => this.setState('idle'), 5000);
    }
  }
  
  setState(state: 'idle' | 'processing' | 'success' | 'error'): void {
    this.state = state;
    this.button.className = `sb-capture-button sb-state-${state}`;
    
    switch (state) {
      case 'processing':
        this.button.textContent = 'Capturing...';
        this.button.disabled = true;
        break;
      case 'success':
        this.button.textContent = '✓ Captured!';
        this.button.disabled = false;
        break;
      case 'error':
        this.button.textContent = '✗ Failed';
        this.button.disabled = false;
        break;
      default:
        this.button.textContent = 'Capture to Second Brain';
        this.button.disabled = false;
    }
  }
}
```

### 3.3 Selective Message Capture

**Feature:**
- User can select specific messages to include in capture
- Checkboxes next to each message
- "Select All" / "Deselect All" toggle
- Selected message indices stored in conversation metadata

**UI Implementation:**
```typescript
class SelectiveCaptureUI {
  private checkboxes: Map<number, HTMLInputElement> = new Map();
  
  injectCheckboxes(messages: Message[]): void {
    messages.forEach((msg, index) => {
      const checkbox = this.createCheckbox(index, msg);
      this.injectCheckbox(checkbox, msg.metadata?.elementId);
      this.checkboxes.set(index, checkbox);
    });
  }
  
  private createCheckbox(index: number, message: Message): HTMLInputElement {
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'sb-message-checkbox';
    checkbox.checked = true; // Default: all selected
    checkbox.dataset.messageIndex = index.toString();
    return checkbox;
  }
  
  getSelectedIndices(): number[] {
    const selected: number[] = [];
    this.checkboxes.forEach((checkbox, index) => {
      if (checkbox.checked) {
        selected.push(index);
      }
    });
    return selected;
  }
  
  filterConversation(conversation: Conversation): Conversation {
    const selectedIndices = this.getSelectedIndices();
    const filteredMessages = conversation.messages.filter((_, index) => 
      selectedIndices.includes(index)
    );
    
    return {
      ...conversation,
      messages: filteredMessages,
      metadata: {
        ...conversation.metadata,
        selectedMessages: selectedIndices
      }
    };
  }
}
```

### 3.4 Batch Capture Mode

**Feature:**
- Capture multiple conversations from conversation list/history
- Batch selection UI in sidebar
- Progress indicator for batch operations
- Error handling per conversation (continue on failure)

**Implementation:**
```typescript
class BatchCaptureManager {
  async captureMultiple(conversationIds: string[]): Promise<BatchResult> {
    const results: Array<{id: string; success: boolean; error?: string}> = [];
    
    for (const id of conversationIds) {
      try {
        // Navigate to conversation (if needed)
        await this.navigateToConversation(id);
        await this.waitForLoad();
        
        // Extract and capture
        const parser = parserRegistry.detectParser();
        if (!parser) continue;
        
        const conversation = parser.extractConversation();
        if (!conversation) continue;
        
        await apiClient.importConversation(conversation);
        results.push({ id, success: true });
      } catch (error) {
        results.push({ id, success: false, error: String(error) });
      }
    }
    
    return {
      total: conversationIds.length,
      successful: results.filter(r => r.success).length,
      failed: results.filter(r => !r.success).length,
      results: results
    };
  }
}
```

### 3.5 Capture History and Status Tracking

**Status Tracking:**
- Track capture status per conversation ID
- Statuses: `pending`, `sent`, `processing`, `completed`, `failed`
- Store in chrome.storage.local
- Display status in UI (icon, badge, tooltip)

**Status Storage:**
```typescript
interface CaptureStatus {
  conversationId: string;
  platform: string;
  status: 'pending' | 'sent' | 'processing' | 'completed' | 'failed';
  capturedAt: string;
  noteId?: string;
  error?: string;
  retryCount?: number;
}

class StatusTracker {
  async saveStatus(status: CaptureStatus): Promise<void> {
    const key = `capture_status_${status.conversationId}`;
    await chrome.storage.local.set({ [key]: status });
  }
  
  async getStatus(conversationId: string): Promise<CaptureStatus | null> {
    const key = `capture_status_${conversationId}`;
    const result = await chrome.storage.local.get(key);
    return result[key] || null;
  }
  
  async updateStatus(
    conversationId: string, 
    updates: Partial<CaptureStatus>
  ): Promise<void> {
    const current = await this.getStatus(conversationId);
    if (current) {
      await this.saveStatus({ ...current, ...updates });
    }
  }
}
```

---

## 4. UI Components & User Experience

### 4.1 Capture Button Placement and Styling

**CSS Styles (Shadow DOM):**
```css
.sb-capture-button {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 10000;
  padding: 12px 24px;
  background: #4F46E5;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  transition: all 0.2s;
}

.sb-capture-button:hover {
  background: #4338CA;
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
}

.sb-capture-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.sb-state-processing {
  background: #6366F1;
  animation: pulse 1.5s infinite;
}

.sb-state-success {
  background: #10B981;
}

.sb-state-error {
  background: #EF4444;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}
```

### 4.2 Action Preview Modal/Panel

**Feature:**
- Extract action items client-side before capture
- Display preview in modal/panel
- Allow user to edit/remove action items
- Highlight action items in conversation

**UI Component:**
```typescript
class ActionPreviewPanel {
  private panel: HTMLElement;
  private actionItems: ActionItem[] = [];
  
  show(conversation: Conversation): void {
    // Extract action items
    this.actionItems = actionExtractor.extract(conversation);
    
    // Create and show panel
    this.panel = this.createPanel();
    this.injectPanel();
  }
  
  private createPanel(): HTMLElement {
    const panel = document.createElement('div');
    panel.className = 'sb-action-preview-panel';
    panel.innerHTML = `
      <div class="sb-panel-header">
        <h3>Action Items Preview</h3>
        <button class="sb-close-btn">×</button>
      </div>
      <div class="sb-action-list">
        ${this.actionItems.map((item, index) => `
          <div class="sb-action-item" data-index="${index}">
            <input type="checkbox" checked data-action-index="${index}">
            <span class="sb-action-text">${item.task}</span>
            <button class="sb-edit-btn" data-action-index="${index}">Edit</button>
          </div>
        `).join('')}
      </div>
      <div class="sb-panel-actions">
        <button class="sb-capture-with-actions">Capture with Actions</button>
        <button class="sb-capture-without-actions">Capture without Actions</button>
      </div>
    `;
    return panel;
  }
  
  getSelectedActions(): ActionItem[] {
    const checkboxes = this.panel.querySelectorAll('input[type="checkbox"]:checked');
    return Array.from(checkboxes).map(cb => {
      const index = parseInt(cb.getAttribute('data-action-index') || '0');
      return this.actionItems[index];
    });
  }
}
```

### 4.3 Todo List Sidebar

**Feature:**
- Sidebar showing todos extracted from conversations
- Link todos to source conversations
- Status tracking (pending, captured, processed)
- Filtering and search

**Sidebar Implementation:**
```typescript
class TodoSidebar {
  private sidebar: HTMLElement;
  private todos: Todo[] = [];
  
  constructor() {
    this.sidebar = this.createSidebar();
    this.injectSidebar();
    this.loadTodos();
  }
  
  addTodo(todo: Todo): void {
    this.todos.push(todo);
    this.saveTodos();
    this.render();
  }
  
  private render(): void {
    const list = this.sidebar.querySelector('.sb-todo-list');
    if (!list) return;
    
    list.innerHTML = this.todos.map(todo => `
      <div class="sb-todo-item" data-todo-id="${todo.id}">
        <input type="checkbox" ${todo.completed ? 'checked' : ''}>
        <span class="sb-todo-text">${todo.text}</span>
        <span class="sb-todo-source">${todo.sourceConversationTitle}</span>
        <span class="sb-todo-status">${todo.status}</span>
      </div>
    `).join('');
  }
  
  private async loadTodos(): Promise<void> {
    const result = await chrome.storage.local.get('todos');
    this.todos = result.todos || [];
    this.render();
  }
  
  private async saveTodos(): Promise<void> {
    await chrome.storage.local.set({ todos: this.todos });
  }
}
```

### 4.4 Settings Panel

**Settings UI:**
- API endpoint configuration
- API key input (masked)
- Platform enable/disable toggles
- Notification preferences
- Capture defaults (auto-capture, selective mode)

**Settings Storage:**
```typescript
interface ExtensionSettings {
  apiEndpoint: string;
  apiKey: string;
  enabledPlatforms: {
    chatgpt: boolean;
    claude: boolean;
  };
  notifications: {
    onCapture: boolean;
    onError: boolean;
    onSync: boolean;
  };
  captureDefaults: {
    autoCapture: boolean;
    selectiveMode: boolean;
    extractActions: boolean;
  };
}

class SettingsManager {
  async getSettings(): Promise<ExtensionSettings> {
    const result = await chrome.storage.sync.get('settings');
    return result.settings || this.getDefaultSettings();
  }
  
  async saveSettings(settings: Partial<ExtensionSettings>): Promise<void> {
    const current = await this.getSettings();
    await chrome.storage.sync.set({
      settings: { ...current, ...settings }
    });
  }
  
  private getDefaultSettings(): ExtensionSettings {
    return {
      apiEndpoint: 'https://api.secondbrain.com',
      apiKey: '',
      enabledPlatforms: {
        chatgpt: true,
        claude: true
      },
      notifications: {
        onCapture: true,
        onError: true,
        onSync: false
      },
      captureDefaults: {
        autoCapture: false,
        selectiveMode: false,
        extractActions: true
      }
    };
  }
}
```

### 4.5 Status Indicators

**Status Badge:**
- Small badge on capture button showing status
- Colors: gray (idle), blue (processing), green (success), red (error)
- Tooltip with detailed status information

**Notification System:**
```typescript
class NotificationManager {
  async showNotification(
    title: string, 
    message: string, 
    type: 'success' | 'error' | 'info' = 'info'
  ): Promise<void> {
    if (await this.shouldShowNotification(type)) {
      chrome.notifications.create({
        type: 'basic',
        iconUrl: chrome.runtime.getURL('icons/icon48.png'),
        title: title,
        message: message
      });
    }
  }
  
  private async shouldShowNotification(type: string): Promise<boolean> {
    const settings = await settingsManager.getSettings();
    return settings.notifications[`on${type.charAt(0).toUpperCase() + type.slice(1)}` as keyof typeof settings.notifications] || false;
  }
}
```

---

## 5. API Integration

### 5.1 Second Brain API Client Implementation

**API Client Class:**
```typescript
class SecondBrainAPIClient {
  private baseUrl: string;
  private apiKey: string;
  
  constructor(baseUrl: string, apiKey: string) {
    this.baseUrl = baseUrl.replace(/\/$/, ''); // Remove trailing slash
    this.apiKey = apiKey;
  }
  
  async importConversation(conversation: Conversation): Promise<ImportResponse> {
    const url = `${this.baseUrl}/api/v1/conversations/import`;
    const idempotencyKey = this.generateIdempotencyKey(conversation);
    
    const requestBody: ConversationImportRequest = {
      data: {
        conversation_id: conversation.id,
        platform: conversation.platform,
        messages: conversation.messages.map(msg => ({
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp
        })),
        metadata: {
          model: conversation.metadata.model,
          created_at: conversation.metadata.conversationDate || 
                     conversation.metadata.capturedAt,
          title: conversation.title
        }
      },
      metadata: {
        idempotency_key: idempotencyKey,
        source_version: '1.0'
      }
    };
    
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json',
        'X-Idempotency-Key': idempotencyKey
      },
      body: JSON.stringify(requestBody)
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new APIError(error.error.code, error.error.message, error.error.details);
    }
    
    return await response.json();
  }
  
  private generateIdempotencyKey(conversation: Conversation): string {
    // Generate UUID v4 for idempotency
    // Use conversation ID + platform as seed for consistency
    return crypto.randomUUID();
  }
  
  async checkCaptureStatus(captureId: string): Promise<CaptureStatusResponse> {
    const url = `${this.baseUrl}/api/v1/capture/status/${captureId}`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      throw new APIError('NOT_FOUND', 'Capture not found');
    }
    
    return await response.json();
  }
}
```

### 5.2 Authentication (API Key Management)

**Secure API Key Storage:**
- Store API key in chrome.storage.sync (encrypted by Chrome)
- Never log or expose API key in console
- Validate API key format on input
- Test API key on save (optional validation endpoint)

**API Key Validation:**
```typescript
class APIKeyManager {
  async saveAPIKey(apiKey: string): Promise<boolean> {
    // Validate format
    if (!this.isValidAPIKey(apiKey)) {
      throw new Error('Invalid API key format');
    }
    
    // Test connection (optional)
    const client = new SecondBrainAPIClient(settings.apiEndpoint, apiKey);
    try {
      // Could call a test endpoint like GET /api/v1/auth/verify
      await this.testConnection(client);
    } catch (error) {
      throw new Error('API key validation failed');
    }
    
    // Save to storage
    await chrome.storage.sync.set({ apiKey: apiKey });
    return true;
  }
  
  async getAPIKey(): Promise<string | null> {
    const result = await chrome.storage.sync.get('apiKey');
    return result.apiKey || null;
  }
  
  private isValidAPIKey(key: string): boolean {
    // Format: sb_live_... or sb_test_...
    return /^sb_(live|test)_[a-zA-Z0-9]{32,}$/.test(key);
  }
  
  private async testConnection(client: SecondBrainAPIClient): Promise<void> {
    // Call health endpoint or verify endpoint
    // This is optional - can skip if no test endpoint exists
  }
}
```

### 5.3 Request Formatting

**Following MASTER_UNIFIED_API_STRATEGY.md Section 4.2:**

Request must match exact schema:
```typescript
interface ConversationImportRequest {
  data: {
    conversation_id: string;
    platform: 'chatgpt' | 'claude' | 'other';
    messages: Array<{
      role: 'user' | 'assistant' | 'system';
      content: string;
      timestamp: string; // ISO 8601
    }>;
    metadata: {
      model?: string;
      created_at: string; // ISO 8601
      title: string;
    };
  };
  metadata: {
    idempotency_key: string; // UUID v4
    source_version: string; // "1.0"
  };
}
```

### 5.4 Response Handling and Error Management

**Response Handling:**
```typescript
interface ImportResponse {
  success: boolean;
  data: {
    conversation_id: string;
    import_id: string;
    notes_created: number;
    actions_extracted: number;
    status: 'completed' | 'processing' | 'failed';
    notes?: Array<{
      note_id: string;
      title: string;
      status: 'ready' | 'inbox';
    }>;
  };
  metadata: {
    request_id: string;
    timestamp: string;
    processing_time_ms: number;
  };
}

class APIError extends Error {
  constructor(
    public code: string,
    public message: string,
    public details?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}

// Error handling
try {
  const response = await apiClient.importConversation(conversation);
  // Handle success
  statusTracker.updateStatus(conversation.id, {
    status: 'sent',
    noteId: response.data.notes?.[0]?.note_id
  });
} catch (error) {
  if (error instanceof APIError) {
    // Handle specific error codes
    switch (error.code) {
      case 'AUTHENTICATION_ERROR':
        // Prompt for new API key
        break;
      case 'RATE_LIMIT_EXCEEDED':
        // Queue for retry
        queueManager.addToQueue(conversation);
        break;
      case 'VALIDATION_ERROR':
        // Log validation error
        console.error('Validation error:', error.details);
        break;
      default:
        // Generic error handling
    }
  }
}
```

### 5.5 Rate Limiting Handling

**Rate Limit Detection:**
```typescript
class RateLimitHandler {
  async handleRateLimit(error: APIError): Promise<void> {
    if (error.code === 'RATE_LIMIT_EXCEEDED') {
      const retryAfter = error.details?.retry_after || 60;
      
      // Queue conversation for retry
      await queueManager.addToQueue(conversation, {
        retryAfter: Date.now() + (retryAfter * 1000),
        retryCount: 0
      });
      
      // Show notification
      notificationManager.showNotification(
        'Rate Limit Exceeded',
        `Will retry in ${retryAfter} seconds`,
        'info'
      );
    }
  }
}
```

---

## 6. Offline Queue & Sync

### 6.1 Offline Queue Storage

**Queue Structure:**
```typescript
interface QueuedConversation {
  id: string; // UUID for queue item
  conversation: Conversation;
  queuedAt: string; // ISO 8601
  retryCount: number;
  lastError?: string;
  retryAfter?: number; // Timestamp
  priority: 'high' | 'normal' | 'low';
}

class QueueManager {
  private readonly MAX_QUEUE_SIZE = 100;
  private readonly MAX_RETRIES = 5;
  
  async addToQueue(
    conversation: Conversation,
    options?: { retryAfter?: number; priority?: 'high' | 'normal' | 'low' }
  ): Promise<void> {
    const queue = await this.getQueue();
    
    // Check queue size
    if (queue.length >= this.MAX_QUEUE_SIZE) {
      // Remove oldest low-priority item
      const lowPriorityIndex = queue.findIndex(item => item.priority === 'low');
      if (lowPriorityIndex >= 0) {
        queue.splice(lowPriorityIndex, 1);
      } else {
        throw new Error('Queue is full');
      }
    }
    
    const queuedItem: QueuedConversation = {
      id: crypto.randomUUID(),
      conversation: conversation,
      queuedAt: new Date().toISOString(),
      retryCount: 0,
      retryAfter: options?.retryAfter,
      priority: options?.priority || 'normal'
    };
    
    queue.push(queuedItem);
    await this.saveQueue(queue);
  }
  
  async getQueue(): Promise<QueuedConversation[]> {
    const result = await chrome.storage.local.get('conversation_queue');
    return result.conversation_queue || [];
  }
  
  async saveQueue(queue: QueuedConversation[]): Promise<void> {
    await chrome.storage.local.set({ conversation_queue: queue });
  }
  
  async removeFromQueue(itemId: string): Promise<void> {
    const queue = await this.getQueue();
    const filtered = queue.filter(item => item.id !== itemId);
    await this.saveQueue(filtered);
  }
}
```

### 6.2 Background Sync Strategy

**Sync Implementation:**
```typescript
class SyncManager {
  private syncInterval: number | null = null;
  
  startBackgroundSync(): void {
    // Sync every 30 seconds when online
    this.syncInterval = window.setInterval(() => {
      if (navigator.onLine) {
        this.syncQueue();
      }
    }, 30000);
    
    // Also sync on online event
    window.addEventListener('online', () => this.syncQueue());
  }
  
  stopBackgroundSync(): void {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }
  }
  
  async syncQueue(): Promise<void> {
    const queue = await queueManager.getQueue();
    const apiClient = await this.getAPIClient();
    
    if (!apiClient) return; // No API key configured
    
    for (const item of queue) {
      // Check retry after
      if (item.retryAfter && Date.now() < item.retryAfter) {
        continue;
      }
      
      // Check retry count
      if (item.retryCount >= 5) {
        // Move to failed queue
        await this.moveToFailedQueue(item);
        continue;
      }
      
      try {
        await apiClient.importConversation(item.conversation);
        
        // Success - remove from queue
        await queueManager.removeFromQueue(item.id);
        
        // Update status
        await statusTracker.updateStatus(item.conversation.id, {
          status: 'sent'
        });
      } catch (error) {
        // Increment retry count
        item.retryCount++;
        item.lastError = String(error);
        
        // Exponential backoff
        item.retryAfter = Date.now() + (Math.pow(2, item.retryCount) * 1000);
        
        await queueManager.saveQueue(queue);
      }
    }
  }
  
  private async getAPIClient(): Promise<SecondBrainAPIClient | null> {
    const settings = await settingsManager.getSettings();
    const apiKey = await apiKeyManager.getAPIKey();
    
    if (!apiKey || !settings.apiEndpoint) {
      return null;
    }
    
    return new SecondBrainAPIClient(settings.apiEndpoint, apiKey);
  }
}
```

### 6.3 Conflict Resolution

**Duplicate Detection:**
- Use idempotency key based on conversation ID + platform
- Server handles duplicates (returns existing result)
- Extension tracks captured conversations to avoid re-queuing

**Conflict Handling:**
```typescript
class ConflictResolver {
  async checkIfAlreadyCaptured(conversationId: string): Promise<boolean> {
    const status = await statusTracker.getStatus(conversationId);
    return status?.status === 'completed' || status?.status === 'sent';
  }
  
  async handleDuplicateResponse(
    conversationId: string,
    response: ImportResponse
  ): Promise<void> {
    // Server returned existing import (idempotency)
    await statusTracker.updateStatus(conversationId, {
      status: 'completed',
      noteId: response.data.notes?.[0]?.note_id
    });
  }
}
```

### 6.4 Queue Size Limits and Cleanup

**Cleanup Strategy:**
- Remove completed items after 7 days
- Remove failed items after 30 days
- Limit queue to 100 items (remove oldest low-priority first)
- Periodic cleanup in background sync

---

## 7. Action Item Extraction (Client-Side Preview)

### 7.1 Client-Side Action Extraction Patterns

**Regex Patterns (from conversation_to_action_extractor.py):**
```typescript
class ActionExtractor {
  extract(conversation: Conversation): ActionItem[] {
    const text = this.conversationToText(conversation);
    const patterns = [
      // Self-referential commitments
      /(?:\bI\s*'\s*ll\b|\bI\s*will\b)\s+([^\.]+)/gi,
      /\bI\s+should\s+([^\.]+)/gi,
      /\bNext\s+time\s+I\s*(?:'\s*ll|will)\s+([^\.]+)/gi,
      // Imperative commands
      /(?:^|\n)(?:-\s*|\*\s*|\d+\.\s*)?\s*([A-Z][a-z]+\b[^\n\r]*)/gm,
      // Action verbs
      /\b(?:create|build|deploy|implement|write|refactor|add|fix)\s+([^\.!?]+)/gi
    ];
    
    const actions: ActionItem[] = [];
    const seen = new Set<string>();
    
    patterns.forEach(pattern => {
      const matches = text.matchAll(pattern);
      for (const match of matches) {
        const task = match[1]?.trim();
        if (task && task.length >= 3 && !seen.has(task.toLowerCase())) {
          seen.add(task.toLowerCase());
          actions.push({
            task: task,
            source: 'regex',
            confidence: 0.7
          });
        }
      }
    });
    
    return actions;
  }
  
  private conversationToText(conversation: Conversation): string {
    return conversation.messages
      .map(msg => msg.content)
      .join('\n');
  }
}
```

### 7.2 Preview Before Capture

**Action Preview UI:**
- Extract actions when user clicks capture button
- Show preview modal with list of actions
- Allow editing/removing actions
- Highlight actions in conversation text

**Highlighting Implementation:**
```typescript
class ActionHighlighter {
  highlightActions(conversation: Conversation, actions: ActionItem[]): void {
    conversation.messages.forEach((msg, msgIndex) => {
      const elementId = msg.metadata?.elementId;
      if (!elementId) return;
      
      const element = document.getElementById(elementId);
      if (!element) return;
      
      actions.forEach(action => {
        if (msg.content.includes(action.task)) {
          this.highlightText(element, action.task);
        }
      });
    });
  }
  
  private highlightText(element: HTMLElement, text: string): void {
    const walker = document.createTreeWalker(
      element,
      NodeFilter.SHOW_TEXT,
      null
    );
    
    const textNodes: Text[] = [];
    let node;
    while (node = walker.nextNode()) {
      textNodes.push(node as Text);
    }
    
    textNodes.forEach(textNode => {
      const content = textNode.textContent || '';
      if (content.includes(text)) {
        const span = document.createElement('span');
        span.className = 'sb-action-highlight';
        span.textContent = text;
        // Replace text with highlighted span
        // (simplified - actual implementation needs careful DOM manipulation)
      }
    });
  }
}
```

### 7.3 Manual Action Item Editing

**Edit Interface:**
- Click "Edit" button on action item
- Inline editing with text input
- Save/Cancel buttons
- Validation (min length, required)

### 7.4 Integration with Second Brain Processing

**Action Items in Request:**
- Include extracted action items in conversation metadata
- Second Brain server will re-extract and validate
- Client-side extraction is preview only (server is source of truth)

---

## 8. Todo/Task Tracking

### 8.1 In-Extension Todo List

**Todo Data Structure:**
```typescript
interface Todo {
  id: string; // UUID
  text: string;
  sourceConversationId: string;
  sourceConversationTitle: string;
  sourcePlatform: string;
  status: 'pending' | 'captured' | 'processed';
  completed: boolean;
  createdAt: string; // ISO 8601
  completedAt?: string; // ISO 8601
  noteId?: string; // Second Brain note ID when processed
}
```

**Todo Manager:**
```typescript
class TodoManager {
  async addTodoFromActions(
    actions: ActionItem[],
    conversation: Conversation
  ): Promise<void> {
    const todos = actions.map(action => ({
      id: crypto.randomUUID(),
      text: action.task,
      sourceConversationId: conversation.id,
      sourceConversationTitle: conversation.title,
      sourcePlatform: conversation.platform,
      status: 'pending' as const,
      completed: false,
      createdAt: new Date().toISOString()
    }));
    
    await this.saveTodos(todos);
    todoSidebar.addTodos(todos);
  }
  
  async updateTodoStatus(
    todoId: string,
    status: 'pending' | 'captured' | 'processed',
    noteId?: string
  ): Promise<void> {
    const todos = await this.getTodos();
    const todo = todos.find(t => t.id === todoId);
    if (todo) {
      todo.status = status;
      if (noteId) todo.noteId = noteId;
      if (status === 'processed') todo.completed = true;
      await this.saveTodos(todos);
    }
  }
  
  async getTodos(): Promise<Todo[]> {
    const result = await chrome.storage.local.get('todos');
    return result.todos || [];
  }
  
  async saveTodos(todos: Todo[]): Promise<void> {
    await chrome.storage.local.set({ todos: todos });
  }
}
```

### 8.2 Link Todos to Captured Conversations

**Linking Logic:**
- When conversation is captured, update related todos to 'captured'
- When Second Brain processes conversation, update todos to 'processed'
- Store noteId in todo for reference

### 8.3 Status Tracking

**Status Updates:**
- `pending`: Todo created, conversation not yet captured
- `captured`: Conversation captured, awaiting Second Brain processing
- `processed`: Second Brain has processed conversation and created notes

**Status Sync:**
- Poll Second Brain API for note status (optional)
- Update todos when status changes
- Show status badges in todo list

### 8.4 Filtering and Search

**Todo Filters:**
- Filter by status (pending, captured, processed)
- Filter by platform (ChatGPT, Claude)
- Filter by date range
- Search by text

**Filter Implementation:**
```typescript
class TodoFilter {
  filter(
    todos: Todo[],
    filters: {
      status?: string;
      platform?: string;
      dateFrom?: string;
      dateTo?: string;
      search?: string;
    }
  ): Todo[] {
    return todos.filter(todo => {
      if (filters.status && todo.status !== filters.status) return false;
      if (filters.platform && todo.sourcePlatform !== filters.platform) return false;
      if (filters.dateFrom && todo.createdAt < filters.dateFrom) return false;
      if (filters.dateTo && todo.createdAt > filters.dateTo) return false;
      if (filters.search && !todo.text.toLowerCase().includes(filters.search.toLowerCase())) return false;
      return true;
    });
  }
}
```

### 8.5 Export Todos to Second Brain

**Export Feature:**
- Export todos as individual captures
- Batch export all pending todos
- Use `/api/v1/capture` endpoint for each todo

---

## 9. Configuration & Settings

### 9.1 API Endpoint Configuration

**Settings UI:**
```html
<div class="sb-settings-panel">
  <h2>Second Brain API Settings</h2>
  
  <div class="sb-setting-item">
    <label for="api-endpoint">API Endpoint</label>
    <input 
      type="url" 
      id="api-endpoint" 
      placeholder="https://api.secondbrain.com"
      value="https://api.secondbrain.com"
    >
    <small>Base URL for Second Brain API</small>
  </div>
  
  <div class="sb-setting-item">
    <label for="api-key">API Key</label>
    <input 
      type="password" 
      id="api-key" 
      placeholder="sb_live_..."
    >
    <button id="test-connection">Test Connection</button>
    <small>Your Second Brain API key (stored securely)</small>
  </div>
</div>
```

### 9.2 API Key Storage (Secure)

**Security Best Practices:**
- Store in chrome.storage.sync (encrypted by Chrome)
- Never log API key
- Mask API key in UI (show only last 4 characters)
- Validate format on input
- Optional: Test connection on save

### 9.3 Default Capture Options

**Capture Defaults:**
- Auto-capture: Automatically capture when conversation changes (default: off)
- Selective mode: Default to selective message capture (default: off)
- Extract actions: Extract action items before capture (default: on)
- Batch mode: Enable batch capture UI (default: off)

### 9.4 Platform Enable/Disable Toggles

**Platform Toggles:**
```typescript
interface PlatformSettings {
  chatgpt: {
    enabled: boolean;
    autoCapture: boolean;
  };
  claude: {
    enabled: boolean;
    autoCapture: boolean;
  };
}
```

### 9.5 Notification Preferences

**Notification Settings:**
- On capture success
- On capture error
- On queue sync
- On todo updates

---

## 10. Testing & Quality Assurance

### 10.1 Unit Test Requirements

**Test Coverage:**
- 100% coverage for core parsers
- 100% coverage for API client
- 100% coverage for action extractor
- 100% coverage for queue manager

**Test Examples:**
```typescript
describe('ChatGPTParser', () => {
  it('should detect ChatGPT page', () => {
    Object.defineProperty(window, 'location', {
      value: { hostname: 'chat.openai.com' }
    });
    const parser = new ChatGPTParser();
    expect(parser.detect()).toBe(true);
  });
  
  it('should extract conversation title', () => {
    document.body.innerHTML = '<input placeholder="Untitled" value="Test Title">';
    const parser = new ChatGPTParser();
    expect(parser.extractTitle()).toBe('Test Title');
  });
  
  it('should extract messages', () => {
    // Mock DOM structure
    const parser = new ChatGPTParser();
    const messages = parser.extractMessages();
    expect(messages.length).toBeGreaterThan(0);
    expect(messages[0]).toHaveProperty('role');
    expect(messages[0]).toHaveProperty('content');
  });
});
```

### 10.2 Integration Test Requirements

**Integration Tests:**
- Test parser + API client integration
- Test queue manager + sync manager integration
- Test UI components + parser integration
- Test settings persistence

### 10.3 E2E Test Scenarios

**E2E Test Cases:**
1. Install extension → Configure API → Capture ChatGPT conversation
2. Capture Claude conversation → Verify API request format
3. Go offline → Capture conversation → Verify queue → Go online → Verify sync
4. Extract action items → Preview → Edit → Capture
5. Batch capture → Verify progress → Verify all captured

**E2E Test Setup:**
```typescript
// tests/e2e/capture-flow.spec.ts
import puppeteer from 'puppeteer';

describe('Capture Flow E2E', () => {
  it('should capture ChatGPT conversation', async () => {
    const browser = await puppeteer.launch();
    const page = await browser.newPage();
    
    // Load extension
    await page.goto('chrome-extension://.../popup.html');
    
    // Configure API
    await page.type('#api-endpoint', 'http://localhost:8080');
    await page.type('#api-key', 'test-key');
    await page.click('#save-settings');
    
    // Navigate to ChatGPT
    await page.goto('https://chat.openai.com');
    
    // Wait for content script
    await page.waitForSelector('#sb-capture-btn');
    
    // Click capture
    await page.click('#sb-capture-btn');
    
    // Verify API call (mock server)
    // Verify success notification
    
    await browser.close();
  });
});
```

### 10.4 Manual Testing Checklist

**Pre-Release Checklist:**
- [ ] Extension installs without errors
- [ ] API key configuration works
- [ ] ChatGPT conversation capture works
- [ ] Claude conversation capture works
- [ ] Action item extraction works
- [ ] Todo list displays correctly
- [ ] Offline queue works
- [ ] Background sync works
- [ ] Error handling works (invalid API key, network error, etc.)
- [ ] Settings persist across browser restarts
- [ ] No console errors
- [ ] No performance issues (memory leaks, etc.)

### 10.5 Browser Compatibility

**Supported Browsers:**
- Chrome 88+ (Manifest V3 support)
- Edge 88+ (Chromium-based)
- Opera 74+ (Chromium-based)

**Not Supported:**
- Firefox (different extension API)
- Safari (different extension API)

---

## Appendix A: Implementation Checklist

### Phase 1: Foundation
- [ ] Set up project structure (TypeScript, Webpack)
- [ ] Create manifest.json (V3)
- [ ] Implement base parser interface
- [ ] Implement parser registry
- [ ] Create API client skeleton

### Phase 2: Platform Parsers
- [ ] Implement ChatGPT parser with DOM selectors
- [ ] ] Implement Claude parser with DOM selectors
- [ ] Test parsers on live sites
- [ ] Handle edge cases (empty conversations, missing elements)

### Phase 3: Core Features
- [ ] Implement capture button
- [ ] Implement conversation monitoring
- [ ] Implement selective capture
- [ ] Implement action item extraction
- [ ] Implement action preview UI

### Phase 4: API Integration
- [ ] Complete API client implementation
- [ ] Implement authentication
- [ ] Implement error handling
- [ ] Implement rate limiting handling
- [ ] Test with Second Brain API

### Phase 5: Advanced Features
- [ ] Implement offline queue
- [ ] Implement background sync
- [ ] Implement todo tracking
- [ ] Implement batch capture
- [ ] Implement status tracking

### Phase 6: UI/UX
- [ ] Design and implement all UI components
- [ ] Implement settings panel
- [ ] Implement notifications
- [ ] Polish styling and animations

### Phase 7: Testing
- [ ] Write unit tests (100% coverage)
- [ ] Write integration tests
- [ ] Write E2E tests
- [ ] Manual testing on all platforms

### Phase 8: Documentation & Release
- [ ] Write user documentation
- [ ] Create screenshots for Chrome Web Store
- [ ] Prepare for Chrome Web Store submission
- [ ] Submit for review

---

## Appendix B: DOM Selector Maintenance

**Important:** DOM selectors may change when ChatGPT/Claude update their UIs. The extension must be resilient:

1. **Multiple Selector Strategies:**
   - Primary selectors (current)
   - Fallback selectors (alternative patterns)
   - Heuristic detection (if selectors fail)

2. **Selector Versioning:**
   - Store selector versions in parser
   - Log selector failures
   - Provide fallback extraction methods

3. **Update Process:**
   - Monitor for selector failures
   - Update selectors when platforms change
   - Release patch updates quickly

---

## Appendix C: Error Scenarios and Handling

### Network Errors
- **Offline**: Queue conversation, show notification
- **Timeout**: Retry with exponential backoff
- **DNS Error**: Show error, suggest checking API endpoint

### API Errors
- **401 Unauthorized**: Prompt for new API key
- **429 Rate Limit**: Queue with retry-after
- **400 Bad Request**: Log error, skip conversation
- **500 Server Error**: Queue for retry

### Parser Errors
- **Selector Not Found**: Log error, use fallback selectors
- **Empty Conversation**: Skip, show warning
- **Malformed Data**: Log error, attempt partial extraction

---

**Last Updated:** January 27, 2025  
**Status:** AUTHORITATIVE SPECIFICATION  
**Next Review:** When ChatGPT/Claude DOM structures change

