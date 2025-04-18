from flask import Flask, render_template, request, redirect, url_for, flash
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'your-secret-key'  # Replace with a secure key

# Initialize Firebase Admin SDK
cred = credentials.Certificate({
  # Placeholder: Replace with your Firebase service account key
  "type": "service_account",
  "project_id": "eed2-lab-asset-management",
  "private_key_id": "YOUR_PRIVATE_KEY_ID",
  "private_key": "YOUR_PRIVATE_KEY",
  "client_email": "YOUR_CLIENT_EMAIL",
  "client_id": "YOUR_CLIENT_ID",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "YOUR_CLIENT_CERT_URL"
})
firebase_admin.initialize_app(cred)
db = firestore.client()

@app.route('/')
def dashboard():
    equipments = db.collection('equipments').get()
    available_count = sum(1 for e in equipments if e.to_dict()['status'] == 'available')
    borrowed_count = sum(1 for e in equipments if e.to_dict()['status'] == 'borrowed')
    maintenance_count = sum(1 for e in equipments if e.to_dict()['status'] == 'maintenance')
    return render_template('dashboard.html', 
                         available_count=available_count,
                         borrowed_count=borrowed_count,
                         maintenance_count=maintenance_count,
                         today=datetime.now().strftime('%Y-%m-%d'))

@app.route('/equipment')
def equipment_list():
    equipments = db.collection('equipments').get()
    equipment_data = [e.to_dict() | {'id': e.id} for e in equipments]
    return render_template('equipment_list.html', equipments=equipment_data)

@app.route('/borrow', methods=['GET', 'POST'])
def borrow_equipment():
    cart = request.form.get('cart', '[]')  # Cart is managed client-side
    if request.method == 'POST':
        purpose = request.form.get('purpose')
        return_date = request.form.get('return_date')
        cart = eval(cart)  # Parse cart from hidden input
        user_id = 'anonymous'  # Placeholder for user ID
        user_name = 'Anonymous'
        
        for item in cart:
            equipment_ref = db.collection('equipments').document(item['id'])
            equipment = equipment_ref.get().to_dict()
            if equipment['quantity'] >= item['requestedQty']:
                equipment_ref.update({
                    'status': 'borrowed',
                    'borrowerId': user_id,
                    'borrowerName': user_name,
                    'checkoutDate': datetime.now().isoformat(),
                    'expectedReturnDate': return_date,
                    'quantity': equipment['quantity'] - item['requestedQty']
                })
                db.collection('history').add({
                    'equipmentId': item['id'],
                    'equipmentName': equipment['name'],
                    'action': 'borrowed',
                    'userId': user_id,
                    'userName': user_name,
                    'date': datetime.now().isoformat(),
                    'purpose': purpose
                })
        flash('Equipment borrowed successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('borrow_form.html', cart=cart, today=datetime.now().strftime('%Y-%m-%d'))

@app.route('/return', methods=['GET', 'POST'])
def return_equipment():
    user_id = 'anonymous'  # Placeholder
    borrowed_items = [e.to_dict() | {'id': e.id} for e in db.collection('equipments').where('borrowerId', '==', user_id).where('status', '==', 'borrowed').get()]
    
    if request.method == 'POST':
        ntid = request.form.get('ntid')
        return_items = request.form.getlist('return_items')
        return_notes = request.form.get('return_notes')
        
        for item_id in return_items:
            equipment_ref = db.collection('equipments').document(item_id)
            equipment = equipment_ref.get().to_dict()
            equipment_ref.update({
                'status': 'available',
                'borrowerId': None,
                'borrowerName': None,
                'checkoutDate': None,
                'expectedReturnDate': None,
                'actualReturnDate': datetime.now().isoformat(),
                'quantity': equipment['quantity'] + 1
            })
            db.collection('history').add({
                'equipmentId': item_id,
                'equipmentName': equipment['name'],
                'action': 'returned',
                'userId': user_id,
                'userName': user_name,
                'date': datetime.now().isoformat(),
                'notes': return_notes
            })
        
        for key in request.form:
            if key.startswith('extend_date_'):
                item_id = key.replace('extend_date_', '')
                new_date = request.form[key]
                if new_date:
                    db.collection('equipments').document(item_id).update({
                        'expectedReturnDate': new_date
                    })
        
        flash('Equipment returned successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('return_form.html', borrowed_items=borrowed_items, today=datetime.now().strftime('%Y-%m-%d'))

@app.route('/history')
def history():
    history = db.collection('history').order_by('date', direction=firestore.Query.DESCENDING).get()
    history_data = [h.to_dict() | {'date': datetime.fromisoformat(h.to_dict()['date']).strftime('%Y-%m-%d %H:%M:%S')} for h in history]
    return render_template('history.html', history=history_data)

@app.route('/add', methods=['GET', 'POST'])
def add_equipment():
    if request.method == 'POST':
        name = request.form.get('name')
        serial_number = request.form.get('serial_number')
        quantity = int(request.form.get('quantity'))
        
        equipment_ref = db.collection('equipments').add({
            'name': name,
            'serialNumber': serial_number,
            'status': 'available',
            'quantity': quantity,
            'createdAt': datetime.now().isoformat()
        })
        db.collection('history').add({
            'equipmentId': equipment_ref[1].id,
            'equipmentName': name,
            'action': 'added',
            'userId': 'system',
            'userName': 'System',
            'date': datetime.now().isoformat()
        })
        flash('Equipment added successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('add_equipment.html')

if __name__ == '__main__':
    app.run(debug=True)
