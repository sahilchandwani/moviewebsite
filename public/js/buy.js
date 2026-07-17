(function () {
  var button = document.getElementById('pay-button');
  var errorBox = document.getElementById('buy-error');
  if (!button) return;

  var csrfToken = document.querySelector('meta[name="csrf-token"]').content;

  function showError(message) {
    errorBox.textContent = message;
    errorBox.hidden = false;
  }

  button.addEventListener('click', function () {
    button.disabled = true;
    errorBox.hidden = true;
    var slug = button.getAttribute('data-slug');

    fetch('/payment/order/' + encodeURIComponent(slug), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-csrf-token': csrfToken },
      credentials: 'same-origin',
    })
      .then(function (res) {
        return res.json().then(function (data) {
          if (!res.ok) throw new Error(data.error || 'Could not start payment.');
          return data;
        });
      })
      .then(function (order) {
        var rzp = new Razorpay({
          key: order.keyId,
          amount: order.amount,
          currency: order.currency,
          order_id: order.orderId,
          name: 'S4 Entertainments',
          description: order.movieTitle,
          prefill: { name: order.userName, email: order.userEmail },
          theme: { color: '#b5442e' },
          handler: function (response) {
            fetch('/payment/verify', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json', 'x-csrf-token': csrfToken },
              credentials: 'same-origin',
              body: JSON.stringify(response),
            })
              .then(function (res) {
                return res.json().then(function (data) {
                  if (!res.ok) throw new Error(data.error || 'Payment verification failed.');
                  return data;
                });
              })
              .then(function (data) {
                window.location.href = data.redirect;
              })
              .catch(function (err) {
                showError(err.message);
                button.disabled = false;
              });
          },
          modal: {
            ondismiss: function () {
              button.disabled = false;
            },
          },
        });
        rzp.on('payment.failed', function (resp) {
          showError('Payment failed: ' + (resp.error && resp.error.description ? resp.error.description : 'please try again.'));
          button.disabled = false;
        });
        rzp.open();
      })
      .catch(function (err) {
        showError(err.message);
        button.disabled = false;
      });
  });
})();
