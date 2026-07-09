class InteractiveReader {
    constructor(config) {
        // Configuration
        this.textId = config.textId;
        this.language = config.language;
        this.sessionId = config.sessionId;
        this.csrfToken = config.csrfToken;
        
        // Text data
        this.processedContent = config.processedContent;
        this.sentences = this.processedContent.sentences || [];
        this.wordFrequencies = this.processedContent.word_frequencies || {};
        
        // User data
        this.knownWords = new Set(config.knownWords || []);
        this.savedWords = new Set(config.savedWords || []);
        
        // State
        this.currentSentenceIndex = 0;
        this.currentWordIndex = 0;
        this.totalWordsRead = 0;
        this.startTime = Date.now();
        this.readingTimer = null;
        this.wordPositions = new Map();
        
        // UI Elements
        this.textDisplay = document.getElementById('textDisplay');
        this.wordModal = new bootstrap.Modal(document.getElementById('wordModal'));
        this.currentWord = null;
        
        // Initialize
        this.init();
    }
    
    init() {
        console.log('Initializing Interactive Reader...');
        
        // Render the text
        this.renderText();
        
        // Start reading timer
        this.startReadingTimer();
        
        // Set up event listeners
        this.setupEventListeners();
        
        // Update initial stats
        this.updateReadingStats();
        
        // Load existing progress
        this.loadExistingProgress();
    }
    
    renderText() {
        console.log('Rendering text with', this.sentences.length, 'sentences');
        
        if (!this.sentences.length) {
            this.textDisplay.innerHTML = `
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle"></i>
                    Text data not available. Please try refreshing the page.
                </div>
            `;
            return;
        }
        
        let html = '';
        let globalWordIndex = 0;
        
        this.sentences.forEach((sentence, sentenceIndex) => {
            const sentenceId = `sentence-${sentenceIndex}`;
            
            html += `<div id="${sentenceId}" class="sentence mb-3">`;
            
            sentence.words.forEach((wordObj, wordIndex) => {
                const wordId = `word-${globalWordIndex}`;
                const cleanWord = wordObj.clean.toLowerCase();
                
                // Determine word class
                let wordClass = 'word';
                if (wordObj.is_punctuation) {
                    wordClass += ' punctuation';
                } else {
                    if (this.knownWords.has(cleanWord)) {
                        wordClass += ' known';
                    }
                    if (this.savedWords.has(cleanWord)) {
                        wordClass += ' saved';
                    }
                }
                
                // Store word position
                this.wordPositions.set(globalWordIndex, {
                    sentenceIndex,
                    wordIndex,
                    cleanWord,
                    original: wordObj.original,
                    isPunctuation: wordObj.is_punctuation
                });
                
                if (!wordObj.is_punctuation) {
                    html += `<span id="${wordId}" class="${wordClass}" 
                               data-word="${cleanWord}"
                               data-original="${wordObj.original}"
                               data-sentence-index="${sentenceIndex}"
                               data-word-index="${wordIndex}"
                               data-global-index="${globalWordIndex}">
                               ${wordObj.original}
                             </span>`;
                } else {
                    html += `<span class="punctuation">${wordObj.original}</span>`;
                }
                
                html += ' ';
                globalWordIndex++;
            });
            
            html += '</div>';
        });
        
        this.textDisplay.innerHTML = html;
        this.totalWords = globalWordIndex;
        
        // Add click handlers to words
        this.addWordClickHandlers();
        
        // Highlight current position
        this.highlightCurrentPosition();
    }
    
    addWordClickHandlers() {
        document.querySelectorAll('.word:not(.punctuation)').forEach(wordEl => {
            wordEl.addEventListener('click', (e) => this.onWordClick(e));
            wordEl.addEventListener('dblclick', (e) => this.onWordDoubleClick(e));
        });
    }
    
    onWordClick(event) {
        const wordEl = event.currentTarget;
        const wordData = {
            clean: wordEl.dataset.word,
            original: wordEl.dataset.original,
            sentence_index: parseInt(wordEl.dataset.sentenceIndex),
            word_index: parseInt(wordEl.dataset.wordIndex),
            global_index: parseInt(wordEl.dataset.globalIndex)
        };
        
        // Mark as clicked
        wordEl.classList.add('clicked');
        
        // Get sentence text
        const sentenceEl = wordEl.closest('.sentence');
        const sentence = sentenceEl ? sentenceEl.textContent.trim() : '';
        
        // Show word info
        this.showWordInfo(wordData, sentence);
        
        // Track click
        this.trackWordClick(wordData);
    }
    
    onWordDoubleClick(event) {
        event.preventDefault();
        const wordEl = event.currentTarget;
        const wordData = {
            clean: wordEl.dataset.word,
            original: wordEl.dataset.original,
            sentence_index: parseInt(wordEl.dataset.sentenceIndex),
            word_index: parseInt(wordEl.dataset.wordIndex),
            global_index: parseInt(wordEl.dataset.globalIndex)
        };
        
        // Get sentence text
        const sentenceEl = wordEl.closest('.sentence');
        const sentence = sentenceEl ? sentenceEl.textContent.trim() : '';
        
        // Save word immediately
        this.saveWordToVocabulary(wordData, sentence);
    }
    
    async showWordInfo(wordData, sentence) {
        this.currentWord = wordData;
        
        // Show loading state
        document.getElementById('wordModalContent').innerHTML = `
            <div class="text-center py-3">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>
        `;
        
        // Fetch word info
        try {
            const response = await fetch(`/content/api/word-info/?word=${encodeURIComponent(wordData.clean)}&language=${this.language}`);
            const wordInfo = await response.json();
            
            // Update modal content
            this.displayWordInfo(wordInfo, sentence);
            
            // Show modal
            this.wordModal.show();
        } catch (error) {
            console.error('Error fetching word info:', error);
            document.getElementById('wordModalContent').innerHTML = `
                <div class="alert alert-danger">
                    <i class="bi bi-exclamation-triangle"></i>
                    Error loading word information. Please try again.
                </div>
            `;
            this.wordModal.show();
        }
    }
    
    displayWordInfo(wordInfo, sentence) {
        const isKnown = this.knownWords.has(wordInfo.word);
        const isSaved = this.savedWords.has(wordInfo.word);
        
        let html = `
            <div class="word-header mb-3">
                <h4 class="mb-1">${wordInfo.word}</h4>
                <div class="d-flex gap-2 mb-2">
                    <span class="badge bg-secondary">${wordInfo.part_of_speech}</span>
                    <span class="badge bg-info">${wordInfo.frequency}</span>
                    ${isKnown ? '<span class="badge bg-success">Known</span>' : ''}
                    ${isSaved ? '<span class="badge bg-primary">Saved</span>' : ''}
                </div>
                <div class="text-muted small">
                    <i class="bi bi-volume-up"></i> ${wordInfo.pronunciation}
                </div>
            </div>
        `;
        
        // Definitions
        if (wordInfo.definitions && wordInfo.definitions.length) {
            html += `
                <div class="mb-3">
                    <h6>Definitions:</h6>
                    <ul class="mb-0">
                        ${wordInfo.definitions.map(def => `<li>${def}</li>`).join('')}
                    </ul>
                </div>
            `;
        }
        
        // Example sentences
        if (wordInfo.example_sentences && wordInfo.example_sentences.length) {
            html += `
                <div class="mb-3">
                    <h6>Examples:</h6>
                    <div class="bg-light p-2 rounded">
                        ${wordInfo.example_sentences.map(sent => `<p class="mb-1"><em>${sent}</em></p>`).join('')}
                    </div>
                </div>
            `;
        }
        
        // Current context
        html += `
            <div class="mb-3">
                <h6>In this text:</h6>
                <div class="bg-light p-2 rounded">
                    <p class="mb-0"><em>"${sentence}"</em></p>
                </div>
            </div>
        `;
        
        // User's own data if exists
        if (wordInfo.user_translation || wordInfo.user_example) {
            html += `
                <div class="mb-3">
                    <h6>Your notes:</h6>
                    ${wordInfo.user_translation ? `<p><strong>Translation:</strong> ${wordInfo.user_translation}</p>` : ''}
                    ${wordInfo.user_example ? `<p><strong>Your example:</strong> ${wordInfo.user_example}</p>` : ''}
                </div>
            `;
        }
        
        document.getElementById('wordModalContent').innerHTML = html;
        document.getElementById('wordModalTitle').textContent = wordInfo.word;
    }
    
    async saveWordToVocabulary(wordData, sentence) {
        try {
            const response = await fetch('/content/save-word/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    word: wordData,
                    text_id: this.textId,
                    sentence: sentence
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Update UI
                const wordEl = document.getElementById(`word-${wordData.global_index}`);
                if (wordEl) {
                    wordEl.classList.add('saved');
                }
                
                // Add to saved words set
                this.savedWords.add(wordData.clean);
                
                // Update saved words count
                this.updateSavedWordsCount();
                
                // Add to saved words list
                this.addToSavedWordsList({
                    word: wordData.clean,
                    original: wordData.original,
                    vocab_id: result.vocab_id
                });
                
                // Show success message
                this.showToast(`"${wordData.original}" saved to vocabulary!`, 'success');
                
                // Close modal if open
                if (this.wordModal) {
                    this.wordModal.hide();
                }
            } else {
                throw new Error(result.error || 'Failed to save word');
            }
        } catch (error) {
            console.error('Error saving word:', error);
            this.showToast('Error saving word. Please try again.', 'danger');
        }
    }
    
    async trackWordClick(wordData) {
        try {
            await fetch('/content/track-click/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    word: wordData,
                    text_id: this.textId
                })
            });
        } catch (error) {
            console.error('Error tracking word click:', error);
        }
    }
    
    updateSavedWordsCount() {
        const countElement = document.getElementById('savedWordsCount');
        if (countElement) {
            countElement.textContent = this.savedWords.size;
        }
    }
    
    addToSavedWordsList(wordData) {
        const savedWordsList = document.getElementById('savedWordsList');
        
        if (savedWordsList && !savedWordsList.querySelector(`[data-word="${wordData.word}"]`)) {
            const listItem = document.createElement('div');
            listItem.className = 'list-group-item';
            listItem.dataset.word = wordData.word;
            
            listItem.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${wordData.original}</strong>
                        <div class="small text-muted">${wordData.word}</div>
                    </div>
                    <a href="/vocabulary/edit/${wordData.vocab_id}/" 
                       class="btn btn-sm btn-outline-secondary">
                        <i class="bi bi-pencil"></i>
                    </a>
                </div>
            `;
            
            // Insert at the beginning
            if (savedWordsList.firstChild && savedWordsList.firstChild.classList.contains('text-center')) {
                savedWordsList.removeChild(savedWordsList.firstChild);
            }
            
            savedWordsList.insertBefore(listItem, savedWordsList.firstChild);
        }
    }
    
    highlightCurrentPosition() {
        // Remove highlight from all sentences
        document.querySelectorAll('.sentence.current').forEach(el => {
            el.classList.remove('current');
        });
        
        // Highlight current sentence
        const currentSentence = document.getElementById(`sentence-${this.currentSentenceIndex}`);
        if (currentSentence) {
            currentSentence.classList.add('current');
            
            // Scroll to current sentence
            currentSentence.scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });
        }
    }
    
    startReadingTimer() {
        this.readingTimer = setInterval(() => {
            this.updateReadingStats();
        }, 1000); // Update every second
    }
    
    updateReadingStats() {
        const elapsedSeconds = Math.floor((Date.now() - this.startTime) / 1000);
        
        // Update time display
        const timeElement = document.getElementById('readingTime');
        if (timeElement) {
            const minutes = Math.floor(elapsedSeconds / 60);
            const seconds = elapsedSeconds % 60;
            timeElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        }
        
        // Update reading speed
        const speedElement = document.getElementById('readingSpeed');
        if (speedElement && elapsedSeconds > 0) {
            const wordsPerMinute = Math.floor((this.totalWordsRead / elapsedSeconds) * 60);
            speedElement.textContent = wordsPerMinute;
        }
        
        // Update position
        const positionElement = document.getElementById('currentPosition');
        if (positionElement) {
            positionElement.textContent = this.totalWordsRead;
        }
        
        // Auto-save progress every 30 seconds
        if (elapsedSeconds % 30 === 0) {
            this.saveProgress();
        }
    }
    
    async saveProgress() {
        try {
            const response = await fetch('/content/update-progress/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    text_id: this.textId,
                    position: this.totalWordsRead,
                    time_spent: Math.floor((Date.now() - this.startTime) / 1000)
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                // Update progress bar
                const progressBar = document.getElementById('readingProgressBar');
                if (progressBar) {
                    progressBar.style.width = `${result.progress}%`;
                    progressBar.setAttribute('aria-valuenow', result.progress);
                }
            }
        } catch (error) {
            console.error('Error saving progress:', error);
        }
    }
    
    async loadExistingProgress() {
        try {
            const response = await fetch(`/content/api/session-progress/${this.sessionId}/`);
            const data = await response.json();
            
            if (data.success) {
                this.totalWordsRead = data.position || 0;
                this.startTime = Date.now() - (data.time_spent * 1000);
                
                // Scroll to last position
                if (data.position > 0) {
                    // Find sentence containing the position
                    let wordCount = 0;
                    for (let i = 0; i < this.sentences.length; i++) {
                        wordCount += this.sentences[i].word_count;
                        if (wordCount >= data.position) {
                            this.currentSentenceIndex = i;
                            break;
                        }
                    }
                    
                    this.highlightCurrentPosition();
                }
            }
        } catch (error) {
            console.error('Error loading progress:', error);
        }
    }
    
    setupEventListeners() {
        // Save to vocab button
        document.getElementById('saveToVocabBtn')?.addEventListener('click', () => {
            if (this.currentWord) {
                const sentenceEl = document.querySelector(`#sentence-${this.currentWord.sentence_index}`);
                const sentence = sentenceEl ? sentenceEl.textContent.trim() : '';
                this.saveWordToVocabulary(this.currentWord, sentence);
            }
        });
        
        // Font size controls
        document.getElementById('fontSizeSmaller')?.addEventListener('click', () => {
            this.adjustFontSize(-1);
        });
        
        document.getElementById('fontSizeReset')?.addEventListener('click', () => {
            this.resetFontSize();
        });
        
        document.getElementById('fontSizeLarger')?.addEventListener('click', () => {
            this.adjustFontSize(1);
        });
        
        // Navigation controls
        document.getElementById('prevSentence')?.addEventListener('click', () => {
            this.navigateToSentence(-1);
        });
        
        document.getElementById('nextSentence')?.addEventListener('click', () => {
            this.navigateToSentence(1);
        });
        
        // Save progress button
        document.getElementById('saveProgress')?.addEventListener('click', () => {
            this.saveProgress();
            this.showToast('Progress saved!', 'success');
        });
        
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Space to show next sentence
            if (e.key === ' ' || e.key === 'Spacebar') {
                e.preventDefault();
                this.navigateToSentence(1);
            }
            // Arrow keys for navigation
            else if (e.key === 'ArrowLeft') {
                this.navigateToSentence(-1);
            }
            else if (e.key === 'ArrowRight') {
                this.navigateToSentence(1);
            }
            // S to save word
            else if (e.key === 's' || e.key === 'S') {
                if (this.currentWord) {
                    const sentenceEl = document.querySelector(`#sentence-${this.currentWord.sentence_index}`);
                    const sentence = sentenceEl ? sentenceEl.textContent.trim() : '';
                    this.saveWordToVocabulary(this.currentWord, sentence);
                }
            }
        });
        
        // Track reading (update word count when scrolling)
        let lastScrollTop = 0;
        const textContainer = this.textDisplay;
        
        textContainer.addEventListener('scroll', () => {
            const scrollTop = textContainer.scrollTop;
            const scrollHeight = textContainer.scrollHeight;
            const clientHeight = textContainer.clientHeight;
            
            // Estimate words read based on scroll position
            const scrollPercentage = scrollTop / (scrollHeight - clientHeight);
            this.totalWordsRead = Math.floor(this.totalWords * scrollPercentage);
            
            // Update current sentence based on visible area
            this.updateCurrentSentenceFromScroll();
        });
    }
    
    adjustFontSize(delta) {
        const currentSize = parseFloat(getComputedStyle(this.textDisplay).fontSize);
        const newSize = currentSize + (delta * 2);
        
        // Limit font size between 14px and 24px
        if (newSize >= 14 && newSize <= 24) {
            this.textDisplay.style.fontSize = `${newSize}px`;
            localStorage.setItem('readerFontSize', newSize);
        }
    }
    
    resetFontSize() {
        this.textDisplay.style.fontSize = '1.1rem';
        localStorage.removeItem('readerFontSize');
    }
    
    navigateToSentence(direction) {
        const newIndex = this.currentSentenceIndex + direction;
        
        if (newIndex >= 0 && newIndex < this.sentences.length) {
            this.currentSentenceIndex = newIndex;
            this.highlightCurrentPosition();
            
            // Update words read count
            this.totalWordsRead = Math.floor(this.totalWords * (newIndex / this.sentences.length));
        }
        
        // If at the end, mark as completed
        if (newIndex >= this.sentences.length - 1) {
            this.markAsCompleted();
        }
    }
    
    updateCurrentSentenceFromScroll() {
        const sentences = this.textDisplay.querySelectorAll('.sentence');
        const viewportTop = this.textDisplay.scrollTop;
        const viewportBottom = viewportTop + this.textDisplay.clientHeight;
        
        for (let i = 0; i < sentences.length; i++) {
            const sentence = sentences[i];
            const rect = sentence.getBoundingClientRect();
            const sentenceTop = rect.top + this.textDisplay.scrollTop;
            const sentenceBottom = sentenceTop + rect.height;
            
            // If sentence is in the middle of the viewport
            if (sentenceTop <= viewportBottom && sentenceBottom >= viewportTop) {
                this.currentSentenceIndex = i;
                this.highlightCurrentPosition();
                break;
            }
        }
    }
    
    async markAsCompleted() {
        try {
            const response = await fetch('/content/mark-completed/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    text_id: this.textId
                })
            });
            
            const result = await response.json();
            
            if (result.success) {
                this.showToast('Congratulations! You finished reading this text!', 'success');
            }
        } catch (error) {
            console.error('Error marking as completed:', error);
        }
    }
    
    showToast(message, type = 'info') {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-bg-${type} border-0 position-fixed`;
        toast.style.top = '20px';
        toast.style.right = '20px';
        toast.style.zIndex = '9999';
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="bi ${type === 'success' ? 'bi-check-circle' : type === 'danger' ? 'bi-exclamation-circle' : 'bi-info-circle'} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove toast after hiding
        toast.addEventListener('hidden.bs.toast', function() {
            toast.remove();
        });
    }
}

// Initialize reader when page loads
document.addEventListener('DOMContentLoaded', function() {
    const readerData = document.getElementById('readerData');
    
    if (readerData) {
        const reader = new InteractiveReader({
            textId: readerData.dataset.textId,
            language: readerData.dataset.textLanguage,
            sessionId: readerData.dataset.sessionId,
            csrfToken: readerData.dataset.csrfToken,
            processedContent: JSON.parse(readerData.dataset.processedContent),
            knownWords: JSON.parse(readerData.dataset.knownWords),
            savedWords: JSON.parse(readerData.dataset.savedWords)
        });
        
        // Make available globally for debugging
        window.reader = reader;
    }
    
    // Mobile sidebar toggle
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.querySelector('.sidebar-container');
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.toggle('show');
        });
    }
});