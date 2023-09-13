// Takes bool, opens history menu if true, closes if false
function open_history_menu(state) {
    if (state) {
        history_menu.style.transform = 'translateY(0)';
    } else {
        history_menu.style.transform = 'translateY(100%)';
    };
};


// Takes bool, shows edit name modal if true, hides if false
function show_edit_modal(state) {
    if (state) {
        edit_modal.classList.remove('-translate-y-full', 'top-0');
        edit_modal.classList.add('translate-y-0', 'top-1/3');
    } else {
        edit_modal.classList.remove('translate-y-0', 'top-1/3');
        edit_modal.classList.add('-translate-y-full', 'top-0');
    }
};


// Close history menu/edit modal when user clicks outside either div
document.addEventListener('click', function(event) {
    if (!history_menu.contains(event.target) && !history_button.contains(event.target)) {
        open_history_menu(false);
    }
    if (!edit_modal.contains(event.target)) {
        show_edit_modal(false);
    }
});


// Request history from backend and add card to history menu for each file
async function load_history() {
    // Request new history contents
    let history_json = await fetch('/get_history');
    history_json = await history_json.json();

    // Fade out old contents then empty div
    history_contents.classList.add('opacity-0');
    await sleep(200);
    history_contents.innerHTML = '';

    // Add card div for each item in JSON
    if (Object.keys(history_json).length) {
        for (const [timestamp, details] of Object.entries(history_json)) {
            history_contents.insertAdjacentHTML('beforeend',
                `<div class="bg-slate-950 rounded-xl p-5 text-white mb-3">
                    <h1 class="text-lg font-semibold">${details.output}</h1>
                    <h1 class="text-md text-zinc-500">${new Date(timestamp.replace(/_/g, ' ')).toLocaleString()}</h1>
                    <div class="flex mt-3">
                        <a class="flex h-10 w-10 bg-zinc-500 rounded-lg text-white ms-auto" href="download/${details.output}">
                            <i class="fas fa-file-download m-auto"></i>
                        </a>
                        <a class="flex h-10 w-10 bg-zinc-500 rounded-lg text-white mx-3 edit-button" data-filename="${details.output}" onclick="edit_file(event);"">
                            <i class="fas fa-pencil-alt m-auto"></i>
                        </a>
                        <a class="flex h-10 w-10 bg-zinc-500 rounded-lg text-white me-auto" data-filename="${details.output}" onclick="delete_file(this);"">
                            <i class="fas fa-trash-alt m-auto"></i>
                        </a>
                    </div>
                </div>
            `);
        };
    } else {
        history_contents.insertAdjacentHTML('beforeend', `<h1 class="text-lg">No files found</h1>`);
    };

    // Fade in new contents
    history_contents.offsetHeight;
    history_contents.classList.remove('opacity-0');
};


// Populate history menu on page load
document.addEventListener("DOMContentLoaded", function() {
    load_history();
});


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

    let response = await fetch('/rename', {
        method: 'POST',
        body: JSON.stringify(payload),
        headers: {
            'Accept': 'application/json, text/plain, */*',
            'Content-Type': 'application/json'
        }
    });
    response = await response.json();
    console.log(`${payload['old']} renamed to ${response['filename']}`);

    // Close modal and reload history contents
    show_edit_modal(false);
    load_history();

    // Change download link if renaming from input below download button
    if (button.id != "edit-button") {
        download_button.href = `download/${response['filename']}`;
        rename_input.dataset.original = response['filename'];
        rename_input.placeholder = response['filename'];
    };
};
