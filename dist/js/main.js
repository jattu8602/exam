
document.addEventListener('DOMContentLoaded', () => {

    // Setup Option Clicks
    const options = document.querySelectorAll('.option-item');
    options.forEach(opt => {
        opt.addEventListener('click', handleOptionClick);
    });

    // Setup Reveal Buttons (Manual override)
    const revealBtns = document.querySelectorAll('.reveal-btn');
    revealBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const card = e.target.closest('.question-card');
            showAnswer(card);
            e.target.style.display = 'none'; // Hide button after reveal
        });
    });
});

function handleOptionClick(e) {
    const option = e.currentTarget;
    const card = option.closest('.question-card');

    // Prevent multiple clicks
    if (card.dataset.answered === "true") return;

    card.dataset.answered = "true";

    // Disable all options in this card
    const allOptions = card.querySelectorAll('.option-item');
    allOptions.forEach(o => o.classList.add('disabled'));

    const selectedValue = option.dataset.option;
    const correctValue = card.dataset.correct;

    if (selectedValue === correctValue) {
        // CORRECT
        option.classList.add('correct');
        // Confetti could go here
    } else {
        // WRONG
        option.classList.add('wrong');

        // Highlight the correct one
        const correctOption = card.querySelector(`.option-item[data-option="${correctValue}"]`);
        if(correctOption) correctOption.classList.add('correct');
    }

    // Auto Reveal Explanation
    showAnswer(card);

    // Hide manual reveal button if it exists
    const btn = card.querySelector('.reveal-btn');
    if(btn) btn.style.display = 'none';
}

function showAnswer(card) {
    const content = card.querySelector('.answer-content');
    if (!content.classList.contains('visible')) {
        content.classList.add('visible');
    }
}
