import {
    show_regen_modal,
    show_error_modal,
} from './modals.js';
import {
    handleDownload,
    load_history,
} from './history.js';

const {
    download_div,
    download_button,
    rename_input,
    error_body,
    regen_body,
    regen_button,
} = window.AppContext;

// Now playing elements
const episode_playing = document.getElementById('episode-playing');
const episode_details = document.getElementById('episode-details');

// Record button elements
const record_button = document.getElementById('record-button');
const record_text = document.getElementById('record-button-text');
const record_spinner = document.getElementById('spinner');

// Track if currently recording + start timestamp
let recording = false;
let start_time = '';


// Update playing now info every 5 seconds (except while recording)
async function update_playing_now() {
    if (!recording) {
        let result = await fetch('/get_playing_now');
        result = await result.json();
        episode_playing.innerHTML = result.title;
        episode_details.innerHTML = result.subtext;
    }
}
update_playing_now();
setInterval(update_playing_now, 5000);


// Called by stopRecording, send post to backend, receive generated filename
async function generateFile() {
    // Send starttime, backend gets endtime + playing file and generates clip
    const response = await fetch('/submit', {
        method: 'POST',
        body: JSON.stringify({ startTime: start_time }),
        headers: {
            Accept: 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
        },
    });
    const data = await response.json();

    if (response.ok) {
        // Add link to download button, clear rename input
        download_button.href = `download/${data.filename}`;
        rename_input.dataset.original = data.filename;
        rename_input.placeholder = data.filename;
        rename_input.value = '';
        console.log(`Generated: ${data.filename}`);

        // Show download button, scroll into view if needed
        download_div.classList.remove('opacity-0', 'pointer-events-none');
        download_div.classList.add('show-result');
        download_div.scrollIntoView({ behavior: 'smooth' });

        // Reload history menu contents
        load_history();
    } else {
        // Show error in modal
        error_body.innerHTML = data.error;
        show_error_modal(true);
        console.log(data);
    }

    // Clear old start_time
    start_time = '';
}


// Called when user clicks record button
async function startRecording() {
    // Change button background to red
    record_button.classList.remove('bg-slate-950');
    record_button.classList.add('bg-red-600', 'scale-110');

    // Prevent changing playing_now contents
    recording = true;

    // Get start timestamp
    const result = await fetch('/get_playtime');
    if (result.ok) {
        const data = await result.json();
        start_time = data.playtime;
    } else {
        console.log('Unable to get start time');
    }

    // Hide download button if visible from previous run
    download_div.classList.add('opacity-0', 'pointer-events-none');
    download_div.classList.remove('show-result');
}
record_button.addEventListener('pointerdown', () => {
    // Do not run if already recording (prevents overwriting start_time if record
    // button becomes stuck and user clicks again to stop recording)
    if (!recording) {
        startRecording();
    }
});


// Called when user releases click on record button
async function stopRecording() {
    // Change button background back
    record_button.classList.remove('bg-red-600', 'scale-110');
    record_button.classList.add('bg-slate-950');

    // Show loading spinner
    record_text.classList.remove('opacity-100');
    record_text.classList.add('opacity-0');
    record_spinner.classList.remove('opacity-0');
    record_spinner.classList.add('opacity-100');

    // Resume updating playing_now contents
    recording = false;

    // Send request to backend, show download button when finished
    // Skip if start_time missing (record pressed while nothing playing)
    if (start_time) {
        try {
            await generateFile();
        } catch (e) {
            // Show error in modal
            error_body.innerHTML = 'Failed due to backend error, see Kodi logs for details';
            show_error_modal(true);
        }
    }

    // Stop loading animation
    record_text.classList.remove('opacity-0');
    record_text.classList.add('opacity-100');
    record_spinner.classList.remove('opacity-100');
    record_spinner.classList.add('opacity-0');
}
// Stop recording when user releases click anywhere on page while recording
// Full-page listener prevents stuck record button if cursor moves during click
document.addEventListener('pointerup', () => {
    if (recording) {
        stopRecording();
    }
});


// Ignore touch scroll while recording (prevents stuck record button on mobile
// if user moves finger around while holding button)
document.addEventListener('touchmove', (event) => {
    if (recording) {
        event.preventDefault();
    }
}, { passive: false });


// Called by button in regenerate modal (shown when attempting to download file
// that no longer exists)
async function regenerate_file(button) {
    // Add loading animation to regen modal
    regen_body.innerHTML = '<div id="spinner" class="loading-animation h-24"><div></div><div></div><div></div><div></div></div>';

    // Send filename to backend, wait for regen to complete
    const response = await fetch('/regenerate', {
        method: 'POST',
        body: JSON.stringify({ filename: button.dataset.target }),
        headers: {
            Accept: 'application/json, text/plain, */*',
            'Content-Type': 'application/json',
        },
    });

    if (response.ok) {
        // Hide modal and download file
        show_regen_modal(false);
        handleDownload(button.dataset.target);
    } else {
        // Show error in modal
        error_body.innerHTML = 'Failed due to backend error, see Kodi logs for details';
        show_regen_modal(false);
        show_error_modal(true);
    }
}
regen_button.addEventListener('click', () => regenerate_file(regen_button));
