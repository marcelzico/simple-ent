// doc2pres/static/doc2pres/js/preview.js
class PresentationPreview {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            width: 800,
            height: 600,
            scale: 0.7,
            ...options
        };
        
        this.currentSlide = 0;
        this.slides = [];
        this.init();
    }
    
    init() {
        if (!this.container) return;
        
        this.setupContainer();
        this.loadSlides();
        this.setupNavigation();
    }
    
    setupContainer() {
        this.container.style.position = 'relative';
        this.container.style.width = `${this.options.width}px`;
        this.container.style.height = `${this.options.height}px`;
        this.container.style.border = '1px solid #ddd';
        this.container.style.backgroundColor = '#f8f9fa';
        
        // Create slide container
        this.slideContainer = document.createElement('div');
        this.slideContainer.className = 'slide-container';
        this.slideContainer.style.width = '100%';
        this.slideContainer.style.height = '100%';
        this.slideContainer.style.position = 'relative';
        
        this.container.appendChild(this.slideContainer);
    }
    
    setupNavigation() {
        // Create navigation buttons
        const navContainer = document.createElement('div');
        navContainer.className = 'preview-navigation';
        navContainer.style.position = 'absolute';
        navContainer.style.bottom = '10px';
        navContainer.style.left = '50%';
        navContainer.style.transform = 'translateX(-50%)';
        navContainer.style.display = 'flex';
        navContainer.style.gap = '10px';
        
        const prevBtn = document.createElement('button');
        prevBtn.innerHTML = '← Previous';
        prevBtn.className = 'btn btn-sm btn-outline-secondary';
        prevBtn.onclick = () => this.prevSlide();
        
        const nextBtn = document.createElement('button');
        nextBtn.innerHTML = 'Next →';
        nextBtn.className = 'btn btn-sm btn-outline-primary';
        nextBtn.onclick = () => this.nextSlide();
        
        const slideCounter = document.createElement('span');
        slideCounter.className = 'slide-counter';
        slideCounter.style.alignSelf = 'center';
        
        this.slideCounter = slideCounter;
        
        navContainer.appendChild(prevBtn);
        navContainer.appendChild(this.slideCounter);
        navContainer.appendChild(nextBtn);
        
        this.container.appendChild(navContainer);
    }
    
    loadSlides() {
        // Load slides from API
        fetch('/doc-to-presentation/api/get-slides-preview/')            
            .then(response => response.json())
            .then(data => {
                this.slides = data.slides;
                this.renderCurrentSlide();
            });
    }
    
    renderCurrentSlide() {
        if (this.slides.length === 0) {
            this.slideContainer.innerHTML = '<div class="no-slides">No slides available</div>';
            return;
        }
        
        const slide = this.slides[this.currentSlide];
        this.renderSlide(slide);
        this.updateNavigation();
    }
    
    renderSlide(slide) {
        const slideElement = this.createSlideElement(slide);
        this.slideContainer.innerHTML = '';
        this.slideContainer.appendChild(slideElement);
    }
    
    createSlideElement(slide) {
        const slideDiv = document.createElement('div');
        slideDiv.className = 'preview-slide';
        slideDiv.style.width = `${this.options.width * this.options.scale}px`;
        slideDiv.style.height = `${this.options.height * this.options.scale}px`;
        slideDiv.style.margin = 'auto';
        slideDiv.style.position = 'relative';
        slideDiv.style.backgroundColor = slide.background_color || '#ffffff';
        slideDiv.style.border = '1px solid #ccc';
        slideDiv.style.boxShadow = '0 4px 6px rgba(0,0,0,0.1)';
        slideDiv.style.padding = '20px';
        slideDiv.style.overflow = 'hidden';
        
        // Add title
        if (slide.title) {
            const title = document.createElement('div');
            title.className = 'slide-title';
            title.style.fontSize = '28px';
            title.style.fontWeight = 'bold';
            title.style.marginBottom = '20px';
            title.style.color = slide.title_color || '#000000';
            title.textContent = slide.title;
            slideDiv.appendChild(title);
        }
        
        // Add content
        if (slide.contents && slide.contents.length > 0) {
            const contentContainer = document.createElement('div');
            contentContainer.className = 'slide-content';
            
            slide.contents.forEach(content => {
                const contentElement = this.createContentElement(content);
                contentContainer.appendChild(contentElement);
            });
            
            slideDiv.appendChild(contentContainer);
        }
        
        return slideDiv;
    }
    
    createContentElement(content) {
        const element = document.createElement('div');
        element.className = 'content-element';
        element.style.marginBottom = '10px';
        
        // Apply styles based on hierarchy
        const fontSize = this.getFontSizeForHierarchy(content.hierarchy);
        element.style.fontSize = `${fontSize}px`;
        element.style.fontFamily = content.font_family || 'Arial, sans-serif';
        element.style.color = content.font_color || '#000000';
        
        if (content.is_bold) {
            element.style.fontWeight = 'bold';
        }
        
        if (content.is_italic) {
            element.style.fontStyle = 'italic';
        }
        
        element.textContent = content.text;
        
        return element;
    }
    
    getFontSizeForHierarchy(hierarchy) {
        const sizeMap = {
            'title_1': 32,
            'title_2': 28,
            'title_3': 24,
            'title_4': 20,
            'title_5': 18,
            'content_1': 24,
            'content_2': 20,
            'content_3': 18,
            'content_4': 16,
            'content_5': 14,
        };
        
        return sizeMap[hierarchy] || 16;
    }
    
    prevSlide() {
        if (this.currentSlide > 0) {
            this.currentSlide--;
            this.renderCurrentSlide();
        }
    }
    
    nextSlide() {
        if (this.currentSlide < this.slides.length - 1) {
            this.currentSlide++;
            this.renderCurrentSlide();
        }
    }
    
    updateNavigation() {
        if (this.slideCounter) {
            this.slideCounter.textContent = `${this.currentSlide + 1} / ${this.slides.length}`;
        }
    }
    
    updateSlide(slideId, slideData) {
        // Update slide in slides array
        const index = this.slides.findIndex(s => s.id === slideId);
        if (index !== -1) {
            this.slides[index] = { ...this.slides[index], ...slideData };
            
            // If current slide is updated, re-render
            if (index === this.currentSlide) {
                this.renderCurrentSlide();
            }
        }
    }
}

// Initialize preview when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.presentationPreview = new PresentationPreview('preview-container', {
        width: 800,
        height: 600,
        scale: 0.7
    });
});

// // doc2pres/static/doc2pres/js/preview.js
// console.log("Preview.js loaded");

// // Basic preview functionality
// class SimplePreview {
//     constructor(containerId) {
//         this.container = document.getElementById(containerId);
//         console.log("Preview initialized for container:", containerId);
//     }
    
//     updateSlide(slideData) {
//         console.log("Updating slide:", slideData);
//         if (this.container) {
//             this.container.innerHTML = '<div class="text-center p-5">Preview will appear here</div>';
//         }
//     }
// }

// // Initialize when page loads
// document.addEventListener('DOMContentLoaded', function() {
//     const previewContainer = document.getElementById('preview-container');
//     if (previewContainer) {
//         console.log("Preview container found, initializing preview");
//         window.preview = new SimplePreview('preview-container');
//     }
// });