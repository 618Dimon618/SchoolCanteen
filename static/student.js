function updateItems(radio, itemId) {
    var form = radio.closest('form');
    var hiddenContainer = form.querySelector('[id^="selected_items"]');

    var categoryInputs = hiddenContainer.querySelectorAll('input[data-category="' + radio.name + '"]');
    categoryInputs.forEach(function(inp) { inp.remove(); });

    var input = document.createElement('input');
    input.type = 'hidden';
    input.name = 'items';
    input.value = itemId;
    input.dataset.category = radio.name;
    hiddenContainer.appendChild(input);
}
