let medicines = [];
let billItems = [];
let currentBill = null;
let selectedBillIndex = null;

const money = value => `₹${Number(value).toFixed(2)}`;

function showSection(id) {
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.toggle('active', b.dataset.section === id));
    document.getElementById('page-title').textContent = id[0].toUpperCase() + id.slice(1);
    if (id === 'medicines') loadMedicines();
    if (id === 'billing') loadMedicines();
    if (id === 'sales') { loadMedicines(); loadSales(); }
}

document.querySelectorAll('.nav-btn').forEach(btn => btn.addEventListener('click', () => showSection(btn.dataset.section)));

async function loadDashboard() {
    const data = await fetch('/api/dashboard').then(r => r.json());
    medicineCount.textContent = data.medicine_count;
    stockCount.textContent = data.stock_count;
    salesCount.textContent = data.sales_count;
    salesTotal.textContent = money(data.sales_total);
    inventoryCost.textContent = money(data.inventory_cost);
    inventoryValue.textContent = money(data.inventory_value);
    profitTotal.textContent = money(data.profit_total);
    lowStock.textContent = data.low_stock;
    expired.textContent = data.expired;
}

async function loadMedicines() {
    const search = encodeURIComponent(document.getElementById('searchInput')?.value || '');
    medicines = await fetch(`/api/medicines?search=${search}`).then(r => r.json());
    const tbody = document.getElementById('medicineTable');
    if (tbody) tbody.innerHTML = medicines.map(m => {
        const expiry = new Date(m.expiry_date);
        const expired = expiry < new Date();
        const low = m.quantity <= m.reorder_level;
        const status = expired ? '<span class="status expired">Expired</span>' : low ? '<span class="status low">Low Stock</span>' : '<span class="status">Available</span>';
        return `<tr><td>${escapeHtml(m.medicine_name)}</td><td>${escapeHtml(m.category)}</td><td>${escapeHtml(m.batch_no || '')}</td><td>${m.expiry_date}</td><td>${money(m.purchase_price)}</td><td>${money(m.selling_price)}</td><td>${money(m.stock_value)}</td><td>${m.quantity}</td><td>${status}</td><td><button class="action-btn" onclick="editMedicine(${m.id})">Edit</button><button class="action-btn" onclick="sellMedicine(${m.id})">Sell</button><button class="action-btn" onclick="deleteMedicine(${m.id})">Delete</button></td></tr>`;
    }).join('');
    const select = document.getElementById('saleMedicine');
    if (select) select.innerHTML = medicines.filter(m => m.quantity > 0).map(m => `<option value="${m.id}">${escapeHtml(m.medicine_name)} — Stock ${m.quantity}</option>`).join('');
    const billSelect = document.getElementById('billMedicine');
    if (billSelect) {
        billSelect.innerHTML = medicines.filter(m => m.quantity > 0).map(m => `<option value="${m.id}">${escapeHtml(m.medicine_name)}</option>`).join('');
        updateBillStock();
    }
}

function updateBillStock() {
    const medicine = medicines.find(m => m.id === Number(document.getElementById('billMedicine')?.value));
    document.getElementById('billStock').textContent = medicine?.quantity ?? 0;
}

function renderBillPreview() {
    const customer = document.getElementById('customerName').value.trim() || 'Walk-in customer';
    const rows = billItems.map((item, index) => `<tr class="bill-item-row ${index === selectedBillIndex ? 'selected' : ''}" data-index="${index}"><td>${escapeHtml(item.medicine_name)}</td><td>${item.quantity}</td><td>${money(item.unit_price)}</td><td>${money(item.total_amount)}</td></tr>`).join('');
    const total = billItems.reduce((sum, item) => sum + item.total_amount, 0);
    document.getElementById('billPreview').innerHTML = `<div class="bill-brand">PHARMACY MANAGEMENT SYSTEM</div><div class="bill-meta"><span>Bill No: ${currentBill?.bill_no || 'Draft'}</span><span>Date: ${currentBill ? new Date(currentBill.bill_date || currentBill.created_at).toLocaleDateString() : new Date().toLocaleDateString()}</span></div><div>Customer: <strong>${escapeHtml(customer)}</strong></div><table><thead><tr><th>Medicine</th><th>Qty</th><th>Price</th><th>Total</th></tr></thead><tbody>${rows || '<tr><td colspan="4" class="empty-bill">Add medicines to start the bill</td></tr>'}</tbody><tfoot><tr><th colspan="3">Grand Total</th><th>${money(total)}</th></tr></tfoot></table>`;
    document.querySelectorAll('.bill-item-row').forEach(row => row.addEventListener('click', () => { selectedBillIndex = Number(row.dataset.index); renderBillPreview(); }));
}

function showBillMessage(message, error = false) {
    const element = document.getElementById('billMessage');
    element.textContent = message;
    element.classList.toggle('error', error);
}

document.getElementById('billMedicine').addEventListener('change', updateBillStock);
document.getElementById('customerName').addEventListener('input', renderBillPreview);
document.getElementById('addToBill').addEventListener('click', () => {
    const medicine = medicines.find(m => m.id === Number(document.getElementById('billMedicine').value));
    const quantity = Number(document.getElementById('billQuantity').value);
    if (!medicine || quantity < 1 || quantity > medicine.quantity) return showBillMessage('Enter a quantity available in stock.', true);
    const existing = billItems.find(item => item.medicine_id === medicine.id);
    if (existing) {
        if (existing.quantity + quantity > medicine.quantity) return showBillMessage('The bill quantity exceeds available stock.', true);
        existing.quantity += quantity;
        existing.total_amount = existing.quantity * existing.unit_price;
    } else {
        billItems.push({medicine_id: medicine.id, medicine_name: medicine.medicine_name, quantity, unit_price: Number(medicine.selling_price), total_amount: quantity * Number(medicine.selling_price)});
    }
    currentBill = null;
    document.getElementById('billStatus').textContent = 'Draft';
    document.getElementById('billQuantity').value = 1;
    showBillMessage('Item added to bill.');
    renderBillPreview();
});
document.getElementById('removeBillItem').addEventListener('click', () => {
    const index = selectedBillIndex === null ? billItems.length - 1 : selectedBillIndex;
    if (index >= 0) billItems.splice(index, 1);
    selectedBillIndex = null;
    renderBillPreview();
});
document.getElementById('clearBill').addEventListener('click', () => {
    billItems = []; currentBill = null; selectedBillIndex = null;
    document.getElementById('billStatus').textContent = 'Draft';
    showBillMessage('Bill cleared.');
    renderBillPreview();
});
document.getElementById('generateBill').addEventListener('click', async () => {
    if (!billItems.length) return showBillMessage('Add at least one medicine first.', true);
    const res = await fetch('/api/bills', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({customer_name: document.getElementById('customerName').value, items: billItems.map(item => ({medicine_id: item.medicine_id, quantity: item.quantity}))})});
    const data = await res.json();
    if (!res.ok) return showBillMessage(data.error || 'Could not generate bill.', true);
    currentBill = data;
    document.getElementById('billStatus').textContent = `Bill ${data.bill_no} saved`;
    showBillMessage('Bill generated and stock updated.');
    renderBillPreview();
    loadMedicines(); loadSales(); loadDashboard();
});
document.getElementById('printBill').addEventListener('click', () => {
    if (!billItems.length) return showBillMessage('Add at least one medicine first.', true);
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`<html><head><title>Bill ${currentBill?.bill_no || ''}</title><style>body{font:14px Arial;padding:30px;color:#172033}h1{text-align:center;font-size:20px}table{width:100%;border-collapse:collapse;margin-top:24px}th,td{padding:10px;border-bottom:1px solid #ddd;text-align:left}tfoot th{text-align:right}</style></head><body>${document.getElementById('billPreview').innerHTML}</body></html>`);
    printWindow.document.close(); printWindow.focus(); printWindow.print();
});
document.getElementById('downloadBill').addEventListener('click', () => {
    if (!billItems.length) return showBillMessage('Add at least one medicine first.', true);
    const payload = currentBill || {bill_no: 'draft', customer_name: document.getElementById('customerName').value || 'Walk-in customer', items: billItems, grand_total: billItems.reduce((sum, item) => sum + item.total_amount, 0)};
    const blob = new Blob([JSON.stringify(payload, null, 2)], {type: 'application/json'});
    const link = document.createElement('a'); link.href = URL.createObjectURL(blob); link.download = `bill-${payload.bill_no}.json`; link.click(); URL.revokeObjectURL(link.href);
});

async function loadSales() {
    const sales = await fetch('/api/sales').then(r => r.json());
    document.getElementById('salesTable').innerHTML = sales.slice(0, 10).map(s => `<tr><td>${escapeHtml(s.medicine_name)}</td><td>${s.quantity}</td><td>${money(s.total_amount)}</td><td>${money(s.profit_amount)}</td><td>${new Date(s.sold_at).toLocaleString()}</td></tr>`).join('');
}

function openMedicineModal(medicine = null) {
    document.getElementById('medicineForm').reset();
    expiryHint.classList.remove('invalid');
    expiryDate.setCustomValidity('');
    document.getElementById('reorderLevel').value = 10;
    document.getElementById('medicineId').value = '';
    document.getElementById('modalTitle').textContent = medicine ? 'Edit Medicine' : 'Add Medicine';
    if (medicine) {
        medicineId.value = medicine.id; medicineName.value = medicine.medicine_name; category.value = medicine.category;
        manufacturer.value = medicine.manufacturer || ''; batchNo.value = medicine.batch_no || ''; expiryDate.value = medicine.expiry_date;
        purchasePrice.value = medicine.purchase_price; sellingPrice.value = medicine.selling_price;
        quantity.value = medicine.quantity; reorderLevel.value = medicine.reorder_level;
    }
    document.getElementById('medicineModal').classList.add('show');
}
function closeMedicineModal() { document.getElementById('medicineModal').classList.remove('show'); }
function editMedicine(id) { const m = medicines.find(x => x.id === id); if (m) openMedicineModal(m); }
function sellMedicine(id) { showSection('sales'); setTimeout(() => saleMedicine.value = id, 50); }

async function deleteMedicine(id) {
    if (!confirm('Delete this medicine?')) return;
    const res = await fetch(`/api/medicines/${id}`, {method: 'DELETE'});
    const data = await res.json();
    alert(data.message || data.error);
    loadMedicines(); loadDashboard();
}

function todayIso() { return new Date().toISOString().slice(0, 10); }
function setExpiryMinimum() {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    expiryDate.min = tomorrow.toISOString().slice(0, 10);
}
setExpiryMinimum();
expiryDate.addEventListener('input', () => {
    expiryHint.classList.toggle('invalid', expiryDate.value <= todayIso());
});

document.getElementById('medicineForm').addEventListener('submit', async e => {
    e.preventDefault();
    if (!expiryDate.value || expiryDate.value <= todayIso()) {
        expiryHint.classList.add('invalid');
        expiryDate.setCustomValidity('Expiry date must be after today.');
        expiryDate.reportValidity();
        return;
    }
    expiryDate.setCustomValidity('');
    const id = medicineId.value;
    const payload = {medicine_name: medicineName.value, category: category.value, manufacturer: manufacturer.value, batch_no: batchNo.value, expiry_date: expiryDate.value, purchase_price: Number(purchasePrice.value), selling_price: Number(sellingPrice.value), quantity: Number(quantity.value), reorder_level: Number(reorderLevel.value)};
    const res = await fetch(id ? `/api/medicines/${id}` : '/api/medicines', {method: id ? 'PUT' : 'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
    const data = await res.json();
    if (!res.ok) return alert(data.error || 'Operation failed');
    closeMedicineModal(); loadMedicines(); loadDashboard();
});

document.getElementById('saleForm').addEventListener('submit', async e => {
    e.preventDefault();
    const res = await fetch('/api/sales', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({medicine_id:Number(saleMedicine.value), quantity:Number(saleQuantity.value)})});
    const data = await res.json();
    if (!res.ok) return alert(data.error || 'Sale failed');
    alert(`Sale recorded. Total: ${money(data.total)}`);
    saleQuantity.value = '';
    loadMedicines(); loadSales(); loadDashboard();
});

function escapeHtml(value) { return String(value ?? '').replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch])); }

loadDashboard();
loadMedicines();
renderBillPreview();
