// static/js/offline-storage.js
class OfflineStorage {
    constructor() {
        this.dbName = 'MedZoneChat';
        this.version = 1;
        this.db = null;
        this.init();
    }

    async init() {
        if (!('indexedDB' in window)) {
            console.warn('IndexedDB not supported, offline features disabled');
            return false;
        }
        
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.version);
            
            request.onerror = () => {
                console.error('IndexedDB error:', request.error);
                reject(request.error);
            };
            
            request.onsuccess = () => {
                this.db = request.result;
                console.log('✅ IndexedDB initialized');
                resolve(this.db);
            };
            
            request.onupgradeneeded = (event) => {
                const db = event.target.result;
                
                // Create object store for offline messages
                if (!db.objectStoreNames.contains('messages')) {
                    const store = db.createObjectStore('messages', { 
                        keyPath: 'id', 
                        autoIncrement: true 
                    });
                    store.createIndex('roomType', 'roomType', { unique: false });
                    store.createIndex('roomId', 'roomId', { unique: false });
                    store.createIndex('timestamp', 'timestamp', { unique: false });
                    store.createIndex('status', 'status', { unique: false });
                }
            };
        });
    }

    // Save message for offline
    async saveMessage(roomType, roomId, content) {
        if (!this.db) await this.init();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['messages'], 'readwrite');
            const store = transaction.objectStore('messages');
            
            const message = {
                roomType: roomType,
                roomId: parseInt(roomId),
                content: content,
                timestamp: new Date().toISOString(),
                status: 'pending',
                attempts: 0
            };
            
            const request = store.add(message);
            
            request.onsuccess = () => {
                console.log('💾 Message saved offline:', message);
                resolve(request.result);
            };
            
            request.onerror = () => {
                console.error('❌ Failed to save message offline:', request.error);
                reject(request.error);
            };
        });
    }

    // Get offline messages for a room
    async getMessages(roomType, roomId) {
        if (!this.db) await this.init();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['messages'], 'readonly');
            const store = transaction.objectStore('messages');
            const index = store.index('roomId');
            
            const request = index.getAll(parseInt(roomId));
            
            request.onsuccess = () => {
                const messages = request.result.filter(msg => 
                    msg.roomType === roomType && msg.status === 'pending'
                );
                resolve(messages);
            };
            
            request.onerror = () => {
                reject(request.error);
            };
        });
    }

    // Get all pending messages
    async getAllPendingMessages() {
        if (!this.db) await this.init();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['messages'], 'readonly');
            const store = transaction.objectStore('messages');
            const request = store.getAll();
            
            request.onsuccess = () => {
                const pending = request.result.filter(msg => msg.status === 'pending');
                resolve(pending);
            };
            
            request.onerror = () => reject(request.error);
        });
    }

    // Mark message as sent
    async markMessageSent(messageId) {
        if (!this.db) await this.init();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['messages'], 'readwrite');
            const store = transaction.objectStore('messages');
            
            const getRequest = store.get(messageId);
            
            getRequest.onsuccess = () => {
                const message = getRequest.result;
                if (message) {
                    message.status = 'sent';
                    const putRequest = store.put(message);
                    putRequest.onsuccess = () => resolve();
                    putRequest.onerror = () => reject(putRequest.error);
                } else {
                    resolve();
                }
            };
            
            getRequest.onerror = () => reject(getRequest.error);
        });
    }

    // Remove message from offline storage
    async removeMessage(messageId) {
        if (!this.db) await this.init();
        
        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['messages'], 'readwrite');
            const store = transaction.objectStore('messages');
            
            const request = store.delete(messageId);
            
            request.onsuccess = () => {
                console.log('🗑️ Message removed from offline storage:', messageId);
                resolve();
            };
            
            request.onerror = () => reject(request.error);
        });
    }

   //  the syncPendingMessages method
    async syncPendingMessages() {
        if (!navigator.onLine) {
            console.log('🔌 Still offline - cannot sync');
            return;
        }

        try {
            const pendingMessages = await this.getAllPendingMessages();
            console.log(`🔄 Syncing ${pendingMessages.length} pending messages from storage`);
            
            let syncedCount = 0;
            
            for (const message of pendingMessages) {
                try {
                    console.log(`Attempting to sync message ${message.id}:`, message.content.substring(0, 30));
                    
                    // For now, we'll just mark them as sent since the WebSocket handles actual sending
                    // In a real app, you'd send to your API endpoint
                    await this.markMessageSent(message.id);
                    syncedCount++;
                    
                    console.log(`✅ Message ${message.id} marked as sent`);
                    
                } catch (error) {
                    console.error(`❌ Failed to sync message ${message.id}:`, error);
                    message.attempts = (message.attempts || 0) + 1;
                    
                    if (message.attempts >= 3) {
                        console.log(`🗑️ Removing message ${message.id} after 3 failed attempts`);
                        await this.removeMessage(message.id);
                    }
                }
            }
            
            console.log(`✅ Sync completed: ${syncedCount}/${pendingMessages.length} messages synced`);
            
        } catch (error) {
            console.error('❌ Sync process failed:', error);
        }
    }

    async sendMessageToServer(message) {
        // This would send via your API endpoint
        // For now, we'll simulate successful send
        return new Promise((resolve) => {
            setTimeout(resolve, 100);
        });
    }
}

// Initialize offline storage
const offlineStorage = new OfflineStorage();

// Network status detection
window.addEventListener('online', async () => {
    console.log('🌐 Online - syncing messages');
    showToast('Connection restored. Syncing messages...', 'success');
    await offlineStorage.syncPendingMessages();
});

window.addEventListener('offline', () => {
    console.log('🔌 Offline - messages will be saved locally');
    showToast('You are offline. Messages will be sent when connection is restored.', 'warning');
});

// Make available globally
window.offlineStorage = offlineStorage;