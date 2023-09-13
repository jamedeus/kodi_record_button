// Called when user clicks record button
async function startRecording() {
    // Change background to red
    record_button.classList.remove("bg-slate-950");
    record_button.classList.add("bg-red-600", "scale-110");

    // Prevent changing playing_now contents
    recording = true;

    // Get start timestamp
    var result = await fetch(`/get_playtime`);
    starttime = await result.json();

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

    // Send request to backend, show download button when finished
    await generateFile();

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
        body: JSON.stringify({"startTime": starttime}),
        headers: {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json'
        }
    });
    const data = await response.json();

    if (response.ok) {
        // Add link to download button
        download_button.href = `download/${data}`;
        rename_input.dataset.original = data;
        rename_input.placeholder = data;
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
};
