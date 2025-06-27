document.addEventListener('DOMContentLoaded', function() {
    const starInputs = document.querySelectorAll('.star-rating input');
    starInputs.forEach(input => {
        input.addEventListener('change', function() {
            const rating = this.value;
            const labels = this.parentElement.querySelectorAll('label');
            labels.forEach((label, index) => {
                if (5 - index <= rating) {
                    label.classList.add('selected');
                } else {
                    label.classList.remove('selected');
                }
            });
        });
    });
});