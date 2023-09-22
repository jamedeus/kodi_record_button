// Called when user clicks record button
async function startRecording() {
    // Change background to red
    record_button.classList.remove("bg-slate-950");
    record_button.classList.add("bg-red-600", "scale-110");

    // Prevent changing playing_now contents
    recording = true;

    // Get start timestamp
    var result = await fetch(`/get_playtime`);
    if (result.ok) {
        start_time = await result.json();
    } else {
        console.log("Unable to get start time");
    };

    // Hide download button if visible from previous run
    download_div.classList.add("opacity-0", "pointer-events-none")
    download_div.classList.remove("show-result")
};
record_button.addEventListener('mousedown', startRecording);
record_button.addEventListener('touchstart', startRecording);


// Called when user releases click on record button
async function stopRecording() {
    // Change background back
    record_button.classList.remove("bg-red-600", "scale-110");
    record_button.classList.add("bg-slate-950");

    // Show loading spinner
    record_text.classList.remove("opacity-100");
    record_text.classList.add("opacity-0");
    record_spinner.classList.remove("opacity-0");
    record_spinner.classList.add("opacity-100");

    // Resume updating playing_now contents
    recording = false;

    // Send request to backend, show download button when finished
    // Skip if start_time missing (record pressed while nothing playing)
    if (start_time) {
        try {
            await generateFile();
        } catch {
            // Show error in modal
            error_body.innerHTML = "Failed due to backend error, see Kodi logs for details";
            show_error_modal(true);
        };
    };

    // Stop loading animation
    record_text.classList.remove("opacity-0");
    record_text.classList.add("opacity-100");
    record_spinner.classList.remove("opacity-100");
    record_spinner.classList.add("opacity-0");
};
record_button.addEventListener('mouseup', stopRecording);
record_button.addEventListener('touchend', stopRecording);


// Called by stopRecording, send post to backend, receive generated filename
async function generateFile() {
    // Send starttime, backend gets endtime + playing file and generates clip
    let response = await fetch('/submit', {
        method: 'POST',
        body: JSON.stringify({"startTime": start_time}),
        headers: {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json'
        }
    });
    const data = await response.json();

    if (response.ok) {
        // Add link to download button, clear rename input
        download_button.href = `download/${data}`;
        rename_input.dataset.original = data;
        rename_input.placeholder = data;
        rename_input.value = '';
        console.log(`Generated: ${data}`);

        // Show download button, scroll into view if needed
        download_div.classList.remove("opacity-0", "pointer-events-none");
        download_div.classList.add("show-result");
        download_div.scrollIntoView({behavior: "smooth"});

        // Reload history menu contents
        load_history();

    } else {
        // Show error in modal
        error_body.innerHTML = data['error'];
        show_error_modal(true);
        console.log(data);
    };

    // Clear old start_time
    start_time = '';
};


// Called by button in regenerate modal (shown when attempting to download file that no longer exists)
async function regenerate_file(button) {
    // Add loading animation to regen modal
    regen_body.innerHTML = `<div id="spinner" class="flex items-center justify-center h-24 loading-animation"><div></div><div></div><div></div><div></div></div>`;

    // Send filename to backend, wait for regen to complete
    let response = await fetch('/regenerate', {
        method: 'POST',
        body: JSON.stringify(button.dataset.target),
        headers: {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json'
        }
    });

    if (response.ok) {
        // Hide modal and download file
        show_regen_modal(false);
        handleDownload(button.dataset.target)
    } else {
        // Show error in modal
        error_body.innerHTML = "Failed due to backend error, see Kodi logs for details";
        show_regen_modal(false);
        show_error_modal(true);
    };
};
