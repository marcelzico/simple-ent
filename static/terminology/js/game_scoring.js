// static/terminology/js/game_scoring.js
class GameScoringSystem {
    constructor(mode, sessionId, csrfToken) {
        this.mode = mode;
        this.sessionId = sessionId;
        this.csrfToken = csrfToken;
        this.baseUrl = '/terminology/api/';
        
        // Game state tracking
        this.questionsData = [];
        this.responseTimes = [];
    }
    
    // Calculate points for correct answer
    calculatePoints(responseTime, currentStreak) {
        const basePoints = 100;
        const speedBonus = this.calculateSpeedBonus(responseTime);
        const streakBonus = this.calculateStreakBonus(currentStreak);
        const modeMultiplier = this.getModeMultiplier();
        
        return Math.floor((basePoints + speedBonus + streakBonus) * modeMultiplier);
    }
    
    calculateSpeedBonus(responseTime) {
        // Faster answers get more points
        if (responseTime < 1.5) return 50;     // Very fast
        if (responseTime < 3) return 30;       // Fast
        if (responseTime < 5) return 15;       // Moderate
        return 0;                              // Slow
    }
    
    calculateStreakBonus(streak) {
        // Bonus for consecutive correct answers
        if (streak >= 10) return 100;
        if (streak >= 7) return 70;
        if (streak >= 5) return 50;
        if (streak >= 3) return 30;
        return 0;
    }
    
    getModeMultiplier() {
        // Different modes have different difficulty multipliers
        const multipliers = {
            'flashcards': 1.0,
            'multiple_choice': 1.2,
            'matching': 1.3,
            'spell_check': 1.5,
            'speed_challenge': 1.5
        };
        return multipliers[this.mode] || 1.0;
    }
    
    // Track question data
    trackQuestion(questionData) {
        this.questionsData.push(questionData);
        if (questionData.responseTime) {
            this.responseTimes.push(questionData.responseTime);
        }
    }
    
    // Calculate final game statistics
    calculateFinalStats(correctCount, totalQuestions, maxStreak, gameDuration) {
        const accuracy = totalQuestions > 0 ? (correctCount / totalQuestions) * 100 : 0;
        const avgResponseTime = this.responseTimes.length > 0 
            ? this.responseTimes.reduce((a, b) => a + b) / this.responseTimes.length 
            : 0;
        
        return {
            accuracy: Math.round(accuracy),
            averageResponseTime: parseFloat(avgResponseTime.toFixed(2)),
            totalResponseTime: this.responseTimes.reduce((a, b) => a + b, 0),
            questionsAttempted: totalQuestions,
            questionsData: this.questionsData
        };
    }
    
    // Save game results to server
    async saveGameResults(gameData) {
        const url = this.baseUrl + 'save-game-result/';
        
        const data = {
            session_id: this.sessionId,
            final_score: gameData.finalScore,
            correct_answers: gameData.correctCount,
            total_questions: gameData.totalQuestions,
            max_streak: gameData.maxStreak,
            duration: gameData.duration,
            mode: this.mode,
            ...this.calculateFinalStats(
                gameData.correctCount,
                gameData.totalQuestions,
                gameData.maxStreak,
                gameData.duration
            )
        };
        
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify(data)
            });
            
            const result = await response.json();
            return result;
        } catch (error) {
            console.error('Error saving game results:', error);
            return { success: false, error: error.message };
        }
    }
    
    // Update session score in real-time
    async updateSessionScore(score, correctCount, totalQuestions, maxStreak) {
        const url = this.baseUrl + 'update-session-score/';
        
        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    score: score,
                    correct_answers: correctCount,
                    total_questions: totalQuestions,
                    max_streak: maxStreak
                })
            });
            
            const result = await response.json();
            return result;
        } catch (error) {
            console.error('Error updating session score:', error);
            return { success: false, error: error.message };
        }
    }
}