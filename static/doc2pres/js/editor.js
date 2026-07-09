// doc2pres/static/doc2pres/js/editor.js
console.log("Editor.js loaded");

// Basic editor functionality
class SimpleEditor {
    constructor() {
        console.log("Editor initialized");
    }
    
    saveChanges() {
        console.log("Saving changes...");
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    console.log("Document loaded, initializing editor");
    window.editor = new SimpleEditor();
});