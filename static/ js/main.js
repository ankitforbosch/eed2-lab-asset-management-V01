let cart = JSON.parse(localStorage.getItem('cart')) || [];

function updateCartBadge() {
  const badge = document.getElementById('cartBadge');
  if (badge) badge.textContent = cart.length;
  const checkoutButton = document.getElementById('checkoutButton');
  if (checkoutButton) checkoutButton.disabled = cart.length === 0;
}

function addToCart(equipmentId, name, serialNumber, quantity) {
  if (!cart.find(item => item.id === equipmentId)) {
    cart.push({ id: equipmentId, name, serialNumber, requestedQty: parseInt(quantity) });
    localStorage.setItem('cart', JSON.stringify(cart));
    updateCartBadge();
  }
}

function removeFromCart(index) {
  cart.splice(index, 1);
  localStorage.setItem('cart', JSON.stringify(cart));
  updateCartBadge();
  renderCart();
}

function renderCart() {
  const cartItems = document.getElementById('cartItems');
  if (cartItems) {
    cartItems.innerHTML = cart.length === 0
      ? '<div class="alert alert-info">Cart is empty</div>'
      : cart.map((item, index) => `
          <div class="cart-item">
            <div class="d-flex justify-content-between align-items-center">
              <div>
                <strong>${item.name}</strong><br>
                <small>Serial: ${item.serialNumber} | Qty: ${item.requestedQty}</small>
              </div>
              <button class="btn btn-sm btn-outline-danger" onclick="removeFromCart(${index})">
                <i class="bi bi-trash"></i>
              </button>
            </div>
          </div>
        `).join('');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  updateCartBadge();
  renderCart();

  // Initialize Firebase
  const firebaseConfig = {
    // REPLACE with your Firebase project's config from Firebase Console > Project settings > Your apps > Web app
    apiKey: "YOUR_API_KEY",
    authDomain: "eed2-lab-asset-management.firebaseapp.com",
    projectId: "eed2-lab-asset-management",
    storageBucket: "eed2-lab-asset-management.appspot.com",
    messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
    appId: "YOUR_APP_ID"
  };
  firebase.initializeApp(firebaseConfig);
  const db = firebase.firestore();

  // Real-time equipment updates
  db.collection('equipments').onSnapshot(snapshot => {
    const availableCount = snapshot.docs.filter(doc => doc.data().status === 'available').length;
    const borrowedCount = snapshot.docs.filter(doc => doc.data().status === 'borrowed').length;
    const maintenanceCount = snapshot.docs.filter(doc => doc.data().status === 'maintenance').length;
    
    const availableElement = document.getElementById('availableCount');
    const borrowedElement = document.getElementById('borrowedCount');
    const maintenanceElement = document.getElementById('maintenanceCount');
    if (availableElement) availableElement.textContent = availableCount;
    if (borrowedElement) borrowedElement.textContent = borrowedCount;
    if (maintenanceElement) maintenanceElement.textContent = maintenanceCount;

    // Update equipment list in modal
    const equipmentList = document.querySelector('.modal-grid');
    if (equipmentList) {
      const searchTerm = document.getElementById('searchInput')?.value.toLowerCase() || '';
      equipmentList.innerHTML = snapshot.docs
        .filter(doc => {
          const data = doc.data();
          return data.name.toLowerCase().includes(searchTerm) ||
                 data.serialNumber.toLowerCase().includes(searchTerm) ||
                 searchTerm === data.status;
        })
        .map(doc => {
          const data = doc.data();
          return `
            <div class="equipment-card">
              <h5>${data.name}</h5>
              <p><strong>Serial:</strong> ${data.serialNumber}</p>
              <p><strong>Quantity:</strong> ${data.quantity}</p>
              ${data.status === 'borrowed' ? `<p><strong>Borrower:</strong> ${data.borrowerName || 'Unknown'}</p>` : ''}
              ${data.status === 'available' ? `<svg class="barcode" id="barcode-${doc.id}"></svg>` : ''}
              ${data.status === 'available' ? `
                <div class="quantity-control mt-2">
                  <input type="number" class="form-control form-control-sm" min="1" max="${data.quantity}" value="1" id="qty-${doc.id}">
                  <button class="btn btn-sm btn-primary" onclick="addToCart('${doc.id}', '${data.name}', '${data.serialNumber}', document.getElementById('qty-${doc.id}').value)">
                    <i class="bi bi-cart-plus"></i> Add
                  </button>
                </div>
              ` : ''}
            </div>
          `;
        }).join('');
      snapshot.docs.forEach(doc => {
        if (doc.data().status === 'available') {
          JsBarcode(`#barcode-${doc.id}`, doc.data().serialNumber, {
            format: 'CODE128',
            lineColor: '#000',
            width: 1.5,
            height: 40,
            displayValue: false
          });
        }
      });
    }
  });

  // Real-time history updates
  db.collection('history').orderBy('date', 'desc').onSnapshot(snapshot => {
    const historyLog = document.querySelector('.history-log');
    if (historyLog) {
      historyLog.innerHTML = snapshot.docs.length === 0
        ? '<div class="alert alert-info">No history records found</div>'
        : snapshot.docs.map(doc => {
            const data = doc.data();
            return `
              <div class="log-entry ${data.action}">
                <div class="d-flex justify-content-between">
                  <div>
                    <strong>${data.userName || 'Unknown'}</strong> ${data.action} <strong>${data.equipmentName || 'Unknown'}</strong><br>
                    <small>Date: ${new Date(data.date).toLocaleString()}</small>
                  </div>
                  <span class="badge bg-${data.action === 'returned' ? 'success' : data.action === 'borrowed' ? 'primary' : 'info'}">
                    ${data.action.charAt(0).toUpperCase() + data.action.slice(1)}
                  </span>
                </div>
                ${data.purpose ? `<p class="mt-1"><em>Purpose: ${data.purpose}</em></p>` : ''}
                ${data.notes ? `<p class="mt-1"><em>Notes: ${data.notes}</em></p>` : ''}
              </div>
            `;
          }).join('');
    }
  });
});
