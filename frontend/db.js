// db.js - Centralized Database for Target Classes fetched from Flask API

// Function to fetch target classes based on detection mode
async function getTargetClasses(mode) {
    try {
        const response = await fetch(`/api/target-classes/${mode}`);
        const data = await response.json();
        return data.classes || [];
    } catch (error) {
        console.error("Error fetching classes from API:", error);
        // Fallback in case backend fails
        if (mode === 'person') return ['person'];
        if (mode === 'mask') return ['mask'];
        if (mode === 'weapon') return ['knife', 'baseball bat'];
        return ['car', 'bicycle', 'bag', 'bottle', 'laptop', 'backpack', 'handbag', 'suitcase', 'cell phone', 'book', 'mouse', 'keyboard', 'scissors', 'clock', 'vase', 'chair', 'cup', 'watch', 'pen', 'tablet'];
    }
}
