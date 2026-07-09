class ECGCanvas {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.scale = 1.0;
        this.offsetX = 0;
        this.offsetY = 0;
        this.isDragging = false;
        this.lastX = 0;
        this.lastY = 0;
        this.currentTool = 'select';
        this.measurements = [];
        this.isMeasuring = false;
        this.currentMeasurement = null;
        
        this.initializeEventListeners();
        this.drawECG();
    }

    initializeEventListeners() {
        // Zoom controls
        const zoomInBtn = document.getElementById('zoomIn');
        const zoomOutBtn = document.getElementById('zoomOut');
        const resetViewBtn = document.getElementById('resetView');
        
        if (zoomInBtn) zoomInBtn.addEventListener('click', () => this.zoom(1.2));
        if (zoomOutBtn) zoomOutBtn.addEventListener('click', () => this.zoom(0.8));
        if (resetViewBtn) resetViewBtn.addEventListener('click', () => this.resetView());

        // Tool selection
        document.querySelectorAll('[data-tool]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('[data-tool]').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.currentTool = e.target.dataset.tool;
                const currentToolElement = document.getElementById('currentTool');
                if (currentToolElement) {
                    currentToolElement.textContent = e.target.textContent;
                }
            });
        });

        // Mouse events for canvas
        this.canvas.addEventListener('mousedown', (e) => this.handleMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.handleMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.handleMouseUp(e));
        this.canvas.addEventListener('wheel', (e) => this.handleWheel(e));
    }

    drawECG() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        this.ctx.save();
        this.ctx.scale(this.scale, this.scale);
        this.ctx.translate(this.offsetX, this.offsetY);

        // Draw ECG grid (1mm squares)
        this.drawGrid();
        
        // Draw sample ECG waveform
        this.drawWaveform();
        
        // Draw measurements
        this.drawMeasurements();

        this.ctx.restore();
    }

    drawGrid() {
        this.ctx.strokeStyle = '#e0e0e0';
        this.ctx.lineWidth = 0.5;

        // Small squares (1mm = 5px at scale 1.0)
        const smallGridSize = 5;
        for (let x = 0; x < this.canvas.width / this.scale; x += smallGridSize) {
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.canvas.height / this.scale);
            this.ctx.stroke();
        }
        for (let y = 0; y < this.canvas.height / this.scale; y += smallGridSize) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.canvas.width / this.scale, y);
            this.ctx.stroke();
        }

        // Large squares (5mm = 25px at scale 1.0)
        this.ctx.strokeStyle = '#b0b0b0';
        this.ctx.lineWidth = 1;
        const largeGridSize = 25;
        for (let x = 0; x < this.canvas.width / this.scale; x += largeGridSize) {
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, this.canvas.height / this.scale);
            this.ctx.stroke();
        }
        for (let y = 0; y < this.canvas.height / this.scale; y += largeGridSize) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(this.canvas.width / this.scale, y);
            this.ctx.stroke();
        }
    }

    drawWaveform() {
        // Sample ECG waveform - you can replace this with real data
        this.ctx.strokeStyle = '#2c5aa0';
        this.ctx.lineWidth = 2;
        this.ctx.beginPath();

        const baseY = 200;
        const amplitude = 30;
        const samples = 1000;

        for (let i = 0; i < samples; i++) {
            const x = i * 0.5; // Compress the waveform
            let y = baseY;

            // Simulate ECG components
            if (i > 100 && i < 150) y += Math.sin((i - 100) * 0.2) * amplitude * 0.3; // P wave
            if (i > 200 && i < 250) y += Math.sin((i - 200) * 0.5) * amplitude; // QRS complex
            if (i > 300 && i < 400) y += Math.sin((i - 300) * 0.1) * amplitude * 0.5; // T wave

            // Add some noise for realism
            y += (Math.random() - 0.5) * 2;

            if (i === 0) {
                this.ctx.moveTo(x, y);
            } else {
                this.ctx.lineTo(x, y);
            }
        }
        this.ctx.stroke();
    }

    drawMeasurements() {
        this.measurements.forEach(measurement => {
            this.ctx.strokeStyle = measurement.color || '#ff4444';
            this.ctx.lineWidth = 2;
            this.ctx.setLineDash([5, 5]);
            
            this.ctx.beginPath();
            this.ctx.moveTo(measurement.x1, measurement.y1);
            this.ctx.lineTo(measurement.x2, measurement.y2);
            this.ctx.stroke();
            this.ctx.setLineDash([]);

            // Draw measurement label
            this.ctx.fillStyle = measurement.color || '#ff4444';
            this.ctx.font = '14px Arial';
            const midX = (measurement.x1 + measurement.x2) / 2;
            const midY = (measurement.y1 + measurement.y2) / 2;
            this.ctx.fillText(measurement.label, midX + 10, midY - 10);
            
            // Draw endpoints
            this.ctx.fillStyle = measurement.color || '#ff4444';
            this.ctx.beginPath();
            this.ctx.arc(measurement.x1, measurement.y1, 3, 0, 2 * Math.PI);
            this.ctx.arc(measurement.x2, measurement.y2, 3, 0, 2 * Math.PI);
            this.ctx.fill();
        });
    }

    handleMouseDown(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = (e.clientX - rect.left - this.offsetX * this.scale) / this.scale;
        const y = (e.clientY - rect.top - this.offsetY * this.scale) / this.scale;

        if (this.currentTool === 'caliper') {
            this.isMeasuring = true;
            this.currentMeasurement = {
                x1: x, y1: y,
                x2: x, y2: y,
                color: '#ff4444',
                label: 'Measuring...'
            };
            this.measurements.push(this.currentMeasurement);
        } else if (this.currentTool === 'select') {
            this.isDragging = true;
            this.lastX = e.clientX;
            this.lastY = e.clientY;
            this.canvas.style.cursor = 'grabbing';
        }
    }

    handleMouseMove(e) {
        const rect = this.canvas.getBoundingClientRect();
        const x = (e.clientX - rect.left - this.offsetX * this.scale) / this.scale;
        const y = (e.clientY - rect.top - this.offsetY * this.scale) / this.scale;

        if (this.isDragging && this.currentTool === 'select') {
            const dx = e.clientX - this.lastX;
            const dy = e.clientY - this.lastY;
            this.offsetX += dx / this.scale;
            this.offsetY += dy / this.scale;
            this.lastX = e.clientX;
            this.lastY = e.clientY;
            this.drawECG();
        } else if (this.isMeasuring && this.currentTool === 'caliper' && this.currentMeasurement) {
            this.currentMeasurement.x2 = x;
            this.currentMeasurement.y2 = y;
            
            // Calculate distance in mm (assuming 5px = 1mm at scale 1.0)
            const distancePx = Math.sqrt(
                Math.pow(this.currentMeasurement.x2 - this.currentMeasurement.x1, 2) + 
                Math.pow(this.currentMeasurement.y2 - this.currentMeasurement.y1, 2)
            );
            const distanceMm = distancePx / 5;
            
            // Calculate time in ms (at 25mm/s paper speed)
            const timeMs = (distanceMm / 25) * 1000;
            
            this.currentMeasurement.label = `${distanceMm.toFixed(1)} mm (${Math.round(timeMs)} ms)`;
            this.drawECG();
        }
    }

    handleMouseUp(e) {
        if (this.currentTool === 'select') {
            this.isDragging = false;
            this.canvas.style.cursor = 'default';
        } else if (this.currentTool === 'caliper') {
            this.isMeasuring = false;
            if (this.currentMeasurement) {
                this.updateMeasurementForm(this.currentMeasurement);
            }
        }
    }

    handleWheel(e) {
        e.preventDefault();
        const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
        this.zoom(zoomFactor, e.clientX, e.clientY);
    }

    zoom(factor, clientX = null, clientY = null) {
        const rect = this.canvas.getBoundingClientRect();
        
        // Get mouse position relative to canvas
        const x = clientX ? (clientX - rect.left) / this.scale : this.canvas.width / (2 * this.scale);
        const y = clientY ? (clientY - rect.top) / this.scale : this.canvas.height / (2 * this.scale);
        
        // Apply zoom
        const newScale = this.scale * factor;
        this.scale = Math.max(0.1, Math.min(5, newScale)); // Limit zoom
        
        // Adjust offset to zoom toward mouse position
        this.offsetX -= (x * (factor - 1));
        this.offsetY -= (y * (factor - 1));
        
        this.drawECG();
    }

    resetView() {
        this.scale = 1.0;
        this.offsetX = 0;
        this.offsetY = 0;
        this.drawECG();
    }

    updateMeasurementForm(measurement) {
        // Extract time from label (format: "X.X mm (Y ms)")
        const timeMatch = measurement.label.match(/\((\d+) ms\)/);
        if (timeMatch) {
            const timeMs = parseInt(timeMatch[1]);
            
            // Determine which interval this measurement represents based on context
            // For now, we'll just show it in the results div
            const resultsDiv = document.getElementById('measurementResults');
            if (resultsDiv) {
                resultsDiv.innerHTML = `
                    <div class="alert alert-info">
                        <strong>Measurement Complete:</strong> ${measurement.label}<br>
                        <small>Use this value for appropriate interval measurement</small>
                    </div>
                `;
            }
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    const canvas = document.getElementById('ecgCanvas');
    if (canvas) {
        new ECGCanvas('ecgCanvas');
    }
});