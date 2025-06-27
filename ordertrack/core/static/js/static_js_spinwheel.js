document.addEventListener('DOMContentLoaded', function() {
    const canvas = document.getElementById('scratch-card');
    const ctx = canvas.getContext('2d');
    const resultText = document.getElementById('result');
    const claimForm = document.getElementById('claim-form');
    const claimBtn = document.getElementById('claim-btn');
    const prizeInput = document.getElementById('prize-value');

    // Get product price and redeemed prize from data attributes
    const productPrice = parseFloat(canvas.dataset.productPrice) || 100;
    const maxPrize = Math.round(productPrice);
    const redeemedPrize = canvas.dataset.redeemedPrize ? parseInt(canvas.dataset.redeemedPrize) : null;

    // Only use the backend value
    function pickPrize() {
        if (redeemedPrize !== null) {
            return { label: String(redeemedPrize), value: redeemedPrize };
        }
        // Optionally: show a placeholder or "?" before spinning
        return { label: "?", value: 0 };
    }

    function drawScratchCard() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.save();
        ctx.font = "bold 2rem Arial";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillStyle = "#333";
        ctx.fillText(prize.label, canvas.width / 2, canvas.height / 2);
        ctx.restore();

        // Draw the scratch overlay only if not already redeemed
        if (redeemedPrize === null) {
            ctx.globalCompositeOperation = "source-over";
            ctx.fillStyle = "#c0c0c0";
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            ctx.save();
            ctx.globalCompositeOperation = "destination-out";
            ctx.font = "1.2rem Arial";
            ctx.textAlign = "center";
            ctx.fillStyle = "rgba(0,0,0,0.5)";
            ctx.fillText("Scratch Here", canvas.width / 2, canvas.height / 2 + 40);
            ctx.restore();
        }
    }

    function scratch(x, y) {
        ctx.save();
        ctx.globalCompositeOperation = "destination-out";
        ctx.beginPath();
        ctx.arc(x, y, 18, 0, 2 * Math.PI);
        ctx.fill();
        ctx.restore();
    }

    function getFilledPercentage() {
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        let scratched = 0;
        for (let i = 0; i < imageData.data.length; i += 4) {
            if (imageData.data[i + 3] === 0) scratched++;
        }
        return scratched / (canvas.width * canvas.height) * 100;
    }

    function revealPrize() {
        if (revealed) return;
        revealed = true;

        let displayPrize = prize; // prize is set by pickPrize()
        resultText.innerHTML = `You won: <strong>${displayPrize.label}</strong>!`;
        resultText.classList.remove('hidden');
        prizeInput.value = displayPrize.value;
        claimForm.classList.remove('hidden');
        claimBtn.classList.remove('hidden');
        canvas.style.pointerEvents = 'none';
    }

    function setupScratchEvents() {
        let rect = canvas.getBoundingClientRect();

        function getXY(e) {
            if (e.touches) {
                const touch = e.touches[0];
                return [touch.clientX - rect.left, touch.clientY - rect.top];
            } else {
                return [e.offsetX, e.offsetY];
            }
        }

        canvas.addEventListener('mousedown', function(e) {
            if (revealed) return;
            isDrawing = true;
            scratch(...getXY(e));
        });
        canvas.addEventListener('mousemove', function(e) {
            if (isDrawing && !revealed) {
                scratch(...getXY(e));
                if (getFilledPercentage() > 40) revealPrize();
            }
        });
        canvas.addEventListener('mouseup', function() {
            isDrawing = false;
        });
        canvas.addEventListener('mouseleave', function() {
            isDrawing = false;
        });

        // Touch events for mobile
        canvas.addEventListener('touchstart', function(e) {
            if (revealed) return;
            isDrawing = true;
            scratch(...getXY(e));
        });
        canvas.addEventListener('touchmove', function(e) {
            if (isDrawing && !revealed) {
                scratch(...getXY(e));
                if (getFilledPercentage() > 40) revealPrize();
            }
            e.preventDefault();
        }, { passive: false });
        canvas.addEventListener('touchend', function() {
            isDrawing = false;
        });
    }

    function startScratchCard() {
        revealed = false;
        prize = pickPrize();
        drawScratchCard();
        canvas.style.pointerEvents = redeemedPrize ? 'none' : 'auto';
        resultText.classList.add('hidden');
        claimForm.classList.add('hidden');
        claimBtn.classList.add('hidden');
        if (!redeemedPrize) setupScratchEvents();
    }

    // Initial setup
    startScratchCard();
    canvas.classList.remove('hidden');
});