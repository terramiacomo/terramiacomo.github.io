function bookingWhatsApp() {
    // validate name input (nome + cognome)
    const name = document.getElementById('booking_name').value.trim();
    if (!name) {
        alert(languageManager.translate('booking_alert_name'));
        return;
    }
    const parts = name.split(/\s+/);
    if (parts.length < 2) {
        alert(languageManager.translate('booking_alert_surname'));
        return;
    }

    const mozz250 = document.getElementById('booking_mozz_250').value;
    const mozz500 = document.getElementById('booking_mozz_500').value;
    const other = document.getElementById('booking_other').value.trim();

    let message = `Salve, vorrei prenotare i seguenti articoli a nome ${name}:\n`;
    if (mozz250 > 0) {
        message += `- ${mozz250}x Mozzarella da 250g\n`;
    }
    if (mozz500 > 0) {
        message += `- ${mozz500}x Mozzarella da 500g\n`;
    }
    if (other) {
        message += `- Altro: ${other}\n`;
    }

    const encodedMessage = encodeURIComponent(message);
    const whatsappURL = `https://wa.me/393759739597?text=${encodedMessage}`;
    window.open(whatsappURL, '_blank');
}