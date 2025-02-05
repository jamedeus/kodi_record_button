const {
    edit_modal,
    edit_input,
    error_modal,
    regen_modal,
} = window.AppContext;


// History menu elements
const history_button = document.getElementById('history-button');
const history_menu = document.getElementById('history-menu');
const history_header = document.getElementById('history-header');
const history_close = document.getElementById('history-close');


// Takes bool, opens history menu if true, closes if false
function open_history_menu(state) {
    if (state) {
        history_menu.style.transform = 'translateY(0)';
    } else {
        history_menu.style.transform = 'translateY(100%)';
    }
}
history_button.addEventListener('click', () => open_history_menu(true));
history_close.addEventListener('click', () => open_history_menu(false));


// Takes bool, shows edit name modal if true, hides if false
function show_edit_modal(state) {
    // Clear input before showing modal
    edit_input.value = '';

    if (state) {
        edit_modal.classList.remove('modal-hide');
        edit_modal.classList.add('translate-y-0', 'lg:top-1/3', 'top-10');
        edit_input.focus();
    } else {
        edit_modal.classList.remove('translate-y-0', 'lg:top-1/3', 'top-10');
        edit_modal.classList.add('modal-hide');
    }
}
document.getElementById('edit-close').addEventListener('click', () => {
    show_edit_modal(false);
});


// Takes bool, shows error modal if true, hides if false
function show_error_modal(state) {
    if (state) {
        error_modal.classList.remove('modal-hide');
        error_modal.classList.add('modal-show');
    } else {
        error_modal.classList.remove('modal-show');
        error_modal.classList.add('modal-hide');
    }
}
document.getElementById('error-close').addEventListener('click', () => {
    show_error_modal(false);
});


// Takes bool, shows regen modal if true, hides if false
function show_regen_modal(state) {
    if (state) {
        regen_modal.classList.remove('modal-hide');
        regen_modal.classList.add('modal-show');
    } else {
        regen_modal.classList.remove('modal-show');
        regen_modal.classList.add('modal-hide');
    }
}
document.getElementById('regen-close').addEventListener('click', () => {
    show_regen_modal(false);
});


// Close all menus/modals when user clicks outside them
document.addEventListener('click', (event) => {
    // Close history menu (unless clicked inside menu)
    if (!history_menu.contains(event.target) && !history_button.contains(event.target)) {
        open_history_menu(false);
    }
    // Close edit modal (unless clicked inside modal)
    if (!edit_modal.contains(event.target)) {
        show_edit_modal(false);
    }
    // Close error modal (unless clicked inside modal)
    if (!error_modal.contains(event.target)) {
        show_error_modal(false);
    }
});


// Close all menus/modals when user presses escape key
document.body.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
        open_history_menu(false);
        show_edit_modal(false);
        show_error_modal(false);
    }
});


// Open history when user presses H key outside input field
document.body.addEventListener('keydown', (event) => {
    if (event.target.tagName !== 'INPUT') {
        if (event.key === 'h') {
            open_history_menu(true);
        }
    }
});


// Used to close history menu when swiping down from top
let y_coord_start = null;

// Store Y coordinate when history menu header touched, used to detect
// user swiping down from top to close menu
history_header.addEventListener('touchstart', (event) => {
    y_coord_start = event.touches[0].clientY;
}, { capture: true });


// Compare coordinates on release, close menu if user swiped down >8 px
history_header.addEventListener('touchmove', (event) => {
    if (y_coord_start === null) {
        return;
    }
    event.preventDefault();

    // Close history menu if user swiped down more than 8 px
    if ((y_coord_start - event.touches[0].clientY) < -8) {
        open_history_menu(false);
    }

    // Reset initial coordinate
    y_coord_start = null;
}, { capture: true });

export {
    open_history_menu,
    show_edit_modal,
    show_regen_modal,
    show_error_modal,
};
