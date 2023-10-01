// Request history from backend and add card to history menu for each file
async function load_history() {
    // Request new history contents
    // Returns array of tuples containing timestamp and filename
    let history_json = await fetch('/get_history');
    history_json = await history_json.json();

    // Clear history search
    history_search.value = '';

    // Add card div for each item in response
    await populate_history_menu(history_json);
};


// Populate history menu on page load
document.addEventListener("DOMContentLoaded", function() {
    load_history();
});


// Takes search_string, requests all history entries with filenames starting
// with search_string and adds card to history menu for each file
async function search_history(search_string) {
    let history_json = await fetch('/search_history', {
        method: 'POST',
        body: JSON.stringify(search_string),
        headers: {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json'
        }
    });
    history_json = await history_json.json();

    // Add card div for each item in response
    await populate_history_menu(history_json);
};


// Update history menu contents on search input
history_search.addEventListener('input', function() {
    const search_string = history_search.value;
    search_history(search_string);
});


// Takes get_history response object, adds card to history menu for each entry
async function populate_history_menu(history_json) {
    // Fade out old contents then empty div
    history_contents.classList.add('opacity-0');
    await sleep(200);
    history_contents.innerHTML = '';

    // Add card div for each item in JSON
    if (Object.keys(history_json).length) {
        history_json.forEach(function(entry) {
            const timestamp = entry[0];
            const filename = entry[1];
            history_contents.insertAdjacentHTML('beforeend',
                `<div class="bg-zinc-900 rounded-xl px-5 py-3 text-white mb-3">
                    <h1 class="text-lg font-semibold line-clamp-1">${filename}</h1>
                    <h1 class="text-md text-zinc-500">${new Date(timestamp.replace(/_/g, ' ')).toLocaleString()}</h1>
                    <div class="flex mt-2">
                        <a class="flex h-9 w-9 lg:h-10 lg:w-10 bg-zinc-500 rounded-lg text-white cursor-pointer ms-auto" onclick="handleDownload('${filename}')">
                            <i class="fas fa-file-download m-auto"></i>
                        </a>
                        <a class="flex h-9 w-9 lg:h-10 lg:w-10 bg-zinc-500 rounded-lg text-white cursor-pointer mx-3 edit-button" data-filename="${filename}" onclick="edit_file(event);"">
                            <i class="fas fa-pencil-alt m-auto"></i>
                        </a>
                        <a class="flex h-9 w-9 lg:h-10 lg:w-10 bg-zinc-500 rounded-lg text-white cursor-pointer me-auto" data-filename="${filename}" onclick="delete_file(this);"">
                            <i class="fas fa-trash-alt m-auto"></i>
                        </a>
                    </div>
                </div>
            `);
        });
    } else {
        history_contents.insertAdjacentHTML('beforeend', `<h1 class="text-lg">No files found</h1>`);
    };

    // Fade in new contents
    history_contents.offsetHeight;
    history_contents.classList.remove('opacity-0');
};


// Called by download buttons in history menu
async function handleDownload(filename) {
    // Request headers only to check if the file still exists
    const response = await fetch(`download/${filename}`, { method: 'HEAD' });

    // Download file if it exists
    if (response.ok) {
        window.location.href = `download/${filename}`;

    // Show regen modal if the file was deleted
    } else {
        regen_body.innerHTML = `${filename} no longer exists, would you like to regenerate it?`;
        regen_button.dataset.target = filename;
        open_history_menu(false);
        show_regen_modal(true);
    };
};


// Called by delete buttons in history menu, deletes mp4 from backend
async function delete_file(button) {
    // Send filename from dataset attribute to backend
    let response = await fetch('/delete', {
        method: 'POST',
        body: JSON.stringify(button.dataset.filename),
        headers: {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json'
        }
    });
    response = await response.text();
    console.log(response)

    // Reload history contents
    load_history();
};


// Called by edit buttons in history menu, opens edit modal for selected mp4
function edit_file(e) {
    event.stopPropagation();

    // Set original name label and input dataset attribute
    const button = event.target.closest('.edit-button');
    original_name.innerHTML = button.dataset.filename;
    edit_input.dataset.original = button.dataset.filename;

    // Close history, open edit modal
    open_history_menu(false);
    show_edit_modal(true);
};


// Called by submit button in edit modal, sends request to backend to rename
async function rename_file(button) {
    // Read old name from dataset attribute, new from input
    if (button.id == "edit-button") {
        // Renaming from history menu
        var payload = {
            'old': edit_input.dataset.original,
            'new': edit_input.value
        }
    } else {
        // Renaming from input below download button
        var payload = {
            'old': rename_input.dataset.original,
            'new': rename_input.value
        }
    };

    // Send request, decode response, hide edit modal
    let response = await fetch('/rename', {
        method: 'POST',
        body: JSON.stringify(payload),
        headers: {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json'
        }
    });
    const data = await response.json();
    show_edit_modal(false);

    if (response.ok) {
        // Reload history contents
        load_history();

        // Detect if file linked by main download button was renamed from history
        // menu instead of the input below download button
        const download_button_link = download_button.href.split('download/')[1];
        const download_button_orig = encodeURIComponent(rename_input.dataset.original);
        if (payload['old'] == download_button_orig && download_button_orig == download_button_link) {
            var edited_from_history = true;
        }

        // Change main download button link if file was renamed from input below
        // download button, or if renamed from history menu
        if (button.id != "edit-button" || edited_from_history) {
            download_button.href = `download/${data['filename']}`;
            rename_input.dataset.original = data['filename'];
            rename_input.placeholder = data['filename'];
            rename_input.value = '';
        };
        console.log(`${payload['old']} renamed to ${data['filename']}`);

    } else {
        // Show error in modal
        error_body.innerHTML = data['error'];
        show_error_modal(true);
        console.log(data);
    };
};
