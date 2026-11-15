
// ==================================
// NAIJAVOICE AI - VOICE RECORDING
// ==================================

// Get HTML elements
const recordBtn = document.getElementById("recordBtn");
const audioFile = document.getElementById("audioInput");
const uploadBtn = document.getElementById("uploadBtn");

// Recording variables
let mediaRecorder;
let audioChunks = [];
let audioBlob = null;
let audioURL = null;
let isRecording = false;

// Create a status area
const statusMessage = document.createElement("p");
statusMessage.id = "recordingStatus";
statusMessage.style.margin = "20px auto";
statusMessage.style.color = "#48dfc1";
statusMessage.style.textAlign = "center";

recordBtn.insertAdjacentElement("afterend", statusMessage);

// Create an audio preview
const audioPreview = document.createElement("audio");
audioPreview.controls = true;
audioPreview.style.display = "none";
audioPreview.style.width = "100%";
audioPreview.style.maxWidth = "400px";
audioPreview.style.margin = "20px auto";

statusMessage.insertAdjacentElement("afterend", audioPreview);

// Show status messages
function showStatus(message) {
    statusMessage.textContent = message;
}

// Start recording
async function startRecording() {

    try {

        const stream = await navigator.mediaDevices.getUserMedia({
            audio: true
        });

        audioChunks = [];

        let options = {};

        if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
            options.mimeType = "audio/webm;codecs=opus";
        }

        mediaRecorder = new MediaRecorder(stream, options);

        mediaRecorder.ondataavailable = function(event) {

            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }

        };

        mediaRecorder.onstop = function() {

            audioBlob = new Blob(audioChunks, {
                type: mediaRecorder.mimeType || "audio/webm"
            });

            if (audioURL) {
                URL.revokeObjectURL(audioURL);
            }

            audioURL = URL.createObjectURL(audioBlob);

            audioPreview.src = audioURL;
            audioPreview.style.display = "block";

            showStatus("Recording saved! You can now play your audio.");

            // Stop microphone access
            stream.getTracks().forEach(track => track.stop());

        };

        mediaRecorder.start();

        isRecording = true;

        recordBtn.textContent = "Stop Recording";

        showStatus("Recording... Speak naturally!");

    } catch (error) {

        console.error("Recording error:", error);

        showStatus("Microphone access failed. Check your browser permissions.");

    }

}

// Stop recording
function stopRecording() {

    if (mediaRecorder && mediaRecorder.state === "recording") {

        mediaRecorder.stop();

        isRecording = false;

        recordBtn.textContent = "Start Recording";

    }

}

// Recording button
recordBtn.addEventListener("click", function() {

    if (!isRecording) {
        startRecording();
    } else {
        stopRecording();
    }

});

// Upload audio and send it to the backend
uploadBtn.addEventListener("click", async function() {

    const file = audioFile.files[0];

    // Use selected file or previously recorded audio
    if (file) {
        audioBlob = file;
    }

    if (!audioBlob) {
        showStatus("Please select or record audio first.");
        return;
    }

    const formData = new FormData();

    formData.append(
        "audio",
        audioBlob,
        file ? file.name : "recording.webm"
    );

    const transcriptionBox = document.getElementById("transcription");

    transcriptionBox.textContent = "Processing your audio...";

    showStatus("Sending audio to NaijaVoice AI...");

    try {

        const response = await fetch("http://127.0.0.1:8000/transcribe", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Transcription failed.");
        }

        transcriptionBox.textContent = data.transcription;

        showStatus(
            data.mode === "demo"
                ? "Demo result received successfully!"
                : "Audio transcription completed!"
        );

    } catch (error) {

        console.error("Transcription error:", error);

        transcriptionBox.textContent = "Could not process audio.";

        showStatus("Error: " + error.message);
    }
});