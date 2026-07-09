// doc2pres/static/doc2pres/js/drag_drop.js
class SlideDragDrop {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.slides = [];
        this.init();
    }
    
    init() {
        if (!this.container) return;
        
        // Make slides draggable
        this.setupDragAndDrop();
        
        // Load existing slides
        this.loadSlides();
    }
    
    setupDragAndDrop() {
        // Use Sortable.js for drag and drop
        if (typeof Sortable !== 'undefined') {
            this.sortable = new Sortable(this.container, {
                animation: 150,
                ghostClass: 'slide-ghost',
                chosenClass: 'slide-chosen',
                dragClass: 'slide-drag',
                onEnd: (evt) => this.onSlideReorder(evt)
            });
        } else {
            // Fallback to native drag and drop
            this.setupNativeDragDrop();
        }
    }
    
    setupNativeDragDrop() {
        const slides = this.container.querySelectorAll('.slide-item');
        
        slides.forEach(slide => {
            slide.setAttribute('draggable', true);
            
            slide.addEventListener('dragstart', (e) => {
                e.dataTransfer.setData('text/plain', slide.dataset.slideId);
                slide.classList.add('dragging');
            });
            
            slide.addEventListener('dragend', () => {
                slide.classList.remove('dragging');
            });
        });
        
        this.container.addEventListener('dragover', (e) => {
            e.preventDefault();
            const afterElement = this.getDragAfterElement(this.container, e.clientY);
            const draggable = document.querySelector('.dragging');
            
            if (afterElement == null) {
                this.container.appendChild(draggable);
            } else {
                this.container.insertBefore(draggable, afterElement);
            }
        });
        
        this.container.addEventListener('drop', (e) => {
            e.preventDefault();
            const slideId = e.dataTransfer.getData('text/plain');
            this.updateSlideOrder();
        });
    }
    
    getDragAfterElement(container, y) {
        const draggableElements = [...container.querySelectorAll('.slide-item:not(.dragging)')];
        
        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;
            
            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    }
    
    onSlideReorder(evt) {
        const slideId = evt.item.dataset.slideId;
        const newIndex = evt.newIndex;
        
        // Update slide order via AJAX
        this.updateSlideOrderOnServer(slideId, newIndex);
    }
    
    updateSlideOrder() {
        const slides = this.container.querySelectorAll('.slide-item');
        const orderData = [];
        
        slides.forEach((slide, index) => {
            orderData.push({
                id: slide.dataset.slideId,
                order: index + 1
            });
        });
        
        this.updateSlideOrderOnServer(orderData);
    }
    
    updateSlideOrderOnServer(orderData) {
        const csrfToken = this.getCSRFToken();
        
        fetch('/doc2pres/api/update-slide-order/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ order: orderData })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log('Slide order updated');
            } else {
                console.error('Error updating slide order:', data.error);
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }
    
    getCSRFToken() {
        const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
        return csrfInput ? csrfInput.value : '';
    }
    
    // In drag_drop.js, update loadSlides function:
    loadSlides() {
        if (!window.API_URLS) {
            console.error('API_URLS not defined');
            return;
        }
        
        fetch(window.API_URLS.getSlides + `?project_id={{ project.id }}`)
            .then(response => response.json())
            .then(data => {
                this.renderSlides(data.slides);
            });
    }
    
    renderSlides(slides) {
        this.container.innerHTML = '';
        
        slides.forEach(slide => {
            const slideElement = this.createSlideElement(slide);
            this.container.appendChild(slideElement);
        });
    }
    
    createSlideElement(slide) {
        const div = document.createElement('div');
        div.className = 'slide-item';
        div.dataset.slideId = slide.id;
        div.innerHTML = `
            <div class="slide-preview">
                <div class="slide-number">${slide.number}</div>
                <div class="slide-title">${slide.title || 'Untitled Slide'}</div>
                <div class="slide-content">${slide.preview || ''}</div>
            </div>
            <div class="slide-actions">
                <button class="btn-edit" onclick="editSlide(${slide.id})">Edit</button>
                <button class="btn-delete" onclick="deleteSlide(${slide.id})">Delete</button>
            </div>
        `;
        
        return div;
    }
}

// Initialize drag and drop when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.slideDragDrop = new SlideDragDrop('slides-container');
});


// // doc2pres/static/doc2pres/js/drag_drop.js
// console.log("DragDrop.js loaded");

// // Basic drag and drop functionality
// class SimpleDragDrop {
//     constructor(containerId) {
//         this.container = document.getElementById(containerId);
//         console.log("DragDrop initialized for container:", containerId);
//     }
// }

// // Initialize when page loads
// document.addEventListener('DOMContentLoaded', function() {
//     const slidesContainer = document.getElementById('slides-container');
//     if (slidesContainer) {
//         console.log("Slides container found, initializing drag drop");
//         window.dragDrop = new SimpleDragDrop('slides-container');
//     }
// });