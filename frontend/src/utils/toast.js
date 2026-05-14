// ToastContainer registers itself via setAddToast() on mount.
let _addToast = null;

export function showToast(msg, type = "success") {
  _addToast?.(msg, type);
}

export function setAddToast(fn) {
  _addToast = fn;
}

export function clearAddToast() {
  _addToast = null;
}
