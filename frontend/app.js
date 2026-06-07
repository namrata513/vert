// frontend/app.js

const API_BASE = "http://127.0.0.1:5000/api";
const USER_ID = localStorage.getItem("verte_user_id");
if (!USER_ID) {
    alert("Please log in first!");
    window.location.href = "auth.html";
}
// DOM Elements references
const webcam = document.getElementById("webcam");
const snapshotCanvas = document.getElementById("snapshot");
const cameraSection = document.getElementById("camera-section");
const guessSection = document.getElementById("guess-section");
const resultSection = document.getElementById("result-section");

// Startup Engine: Request hardware video streams immediately on load
async function initializeWebcam() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false });
        webcam.srcObject = stream;
    } catch (err) {
        console.error("Webcam access denied or unavailable:", err);
        alert("Could not access your camera. Make sure permissions are allowed!");
    }
}

// Capture current video matrix frame and pipe it over HTTP multipart streams
document.getElementById("btn-scan").addEventListener("click", async () => {
    const ctx = snapshotCanvas.getContext("2d");
    snapshotCanvas.width = webcam.videoWidth || 640;
    snapshotCanvas.height = webcam.videoHeight || 480;
    
    // Draw current freeze frame bounding frame array block
    ctx.drawImage(webcam, 0, 0, snapshotCanvas.width, snapshotCanvas.height);
    
    // Extract canvas drawing structures into raw file blobs
    snapshotCanvas.toBlob(async (blob) => {
        const formData = new FormData();
        formData.append("image", blob, "scan.jpg");
        formData.append("user_id", USER_ID);

        try {
            document.getElementById("btn-scan").innerText = "⏳ AI Analyzing...";
            
            const response = await fetch(`${API_BASE}/upload`, { method: "POST", body: formData });
            const data = await response.json();
            
            if (response.ok) {
                // Advance game phase to the User Guess Selection step
                cameraSection.classList.add("hidden");
                guessSection.classList.remove("hidden");
            } else {
                alert(`Upload failed: ${data.error}`);
            }
        } catch (err) {
            console.error(err);
            alert("Backend server offline. Make sure main.py is running on port 5000!");
        } finally {
            document.getElementById("btn-scan").innerText = "📸 Scan Waste Item";
        }
    }, "image/jpeg");
});

// Capture Option Choice clicks and send verification evaluation data requests
document.querySelectorAll(".btn-choice").forEach(button => {
    button.addEventListener("click", async (e) => {
        const selectedGuess = e.currentTarget.getAttribute("data-choice");
        
        try {
            const response = await fetch(`${API_BASE}/verify-guess`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ user_id: USER_ID, guess: selectedGuess })
            });
            const data = await response.json();
            
            if (response.ok) {
                renderEvaluationScreen(data);
            } else {
                alert(data.error);
            }
        } catch (err) {
            alert("Error sending verification response to server.");
        }
    });
});

// Update interface parameters based on structural evaluation parameters
function renderEvaluationScreen(data) {
    guessSection.classList.add("hidden");
    resultSection.classList.remove("hidden");
    
    // Update live layout display parameters
    document.getElementById("stat-points").innerText = data.updated_stats.total_points;
    document.getElementById("stat-streak").innerText = `🌿 ${data.updated_stats.streak_count} days`;
    
    const titleElement = document.getElementById("result-title");
    const textElement = document.getElementById("result-text");
    const iconElement = document.getElementById("result-icon");
    
    if (data.correct) {
        titleElement.className = "text-2xl font-black text-emerald-600";
        titleElement.innerText = "Correct Choice!";
        iconElement.innerText = "🌿✨";
        textElement.innerText = data.message;
    } else {
        titleElement.className = "text-2xl font-black text-amber-600";
        titleElement.innerText = "Not Quite!";
        iconElement.innerText = "🍂";
        textElement.innerText = data.message;
    }
}

// Reset visibility frames back to step 1 camera viewport hooks
document.getElementById("btn-reset").addEventListener("click", () => {
    resultSection.classList.add("hidden");
    cameraSection.classList.remove("hidden");
});

// Run webcam startup on file load initialization parameters
initializeWebcam();

// Append this to the bottom of frontend/app.js

document.getElementById("file-input").addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("image", file);
    formData.append("user_id", USER_ID);

    try {
        // Change the UI text to show it's communicating with the model
        const label = document.querySelector('label[for="file-input"]');
        label.innerText = "⏳ AI Analyzing File...";

        const response = await fetch(`${API_BASE}/upload`, { 
            method: "POST", 
            body: formData 
        });
        const data = await response.json();

        if (response.ok) {
            // Smoothly move the user into the gamified guess menu phase!
            cameraSection.classList.add("hidden");
            guessSection.classList.remove("hidden");
        } else {
            alert(`Error: ${data.error}`);
        }
    } catch (err) {
        alert("Backend offline. Please make sure main.py is running on port 5000.");
    } finally {
        document.querySelector('label[for="file-input"]').innerText = "📁 Upload Image File";
        // Reset the input so you can upload the same file again if needed
        e.target.value = ""; 
    }
});
// Append this to the very bottom of frontend/app.js to sync scores on page load

async function syncDashboardMetrics() {
    if (!USER_ID) return;
    
    try {
        const response = await fetch(`${API_BASE}/user-stats/${USER_ID}`);
        if (response.ok) {
            const stats = await response.json();
            // Update the HTML counters immediately with database realities!
            document.getElementById("stat-points").innerText = stats.total_points;
            document.getElementById("stat-streak").innerText = `🌿 ${stats.streak_count} days`;
        }
    } catch (err) {
        console.error("Failed to sync historical leaderboard metrics from SQLite:", err);
    }
}

// Execute the fetch configuration setup immediately
syncDashboardMetrics();