// Called when user clicks record button
async function startRecording() {
    console.log("Start recording");
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
    console.log("Stop recording");
    // Change background back
    record_button.classList.remove("bg-red-600", "scale-110");
    record_button.classList.add("bg-slate-950");

    // Show loading spinner
    record_text.classList.remove("opacity-100");
    record_text.classList.add("opacity-0");
    record_spinner.classList.remove("opacity-0");
    record_spinner.classList.add("opacity-100");

    // Send request to backend, show download button when finished
    console.log("Calling generateFile");
    await generateFile();
    console.log("generateFile finished");

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
    console.log("generateFile called");
    let response = await fetch('/submit', {
        method: 'POST',
        body: JSON.stringify({"startTime": starttime}),
        headers: {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json'
        }
    });

    // Add link to download button
    const filename = await response.json();
    download_button.href = `download/${filename}`;
    rename_input.dataset.original = filename;
    rename_input.placeholder = filename;
    console.log(filename);

    // Show download button, scroll into view if needed
    download_div.classList.remove("opacity-0", "pointer-events-none");
    download_div.classList.add("show-result");
    download_div.scrollIntoView({behavior: "smooth"});

    // Reload history menu contents
    load_history();
};
