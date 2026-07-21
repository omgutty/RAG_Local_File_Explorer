/* Upload page — column selector helpers */

document.addEventListener('DOMContentLoaded', () => {
  const textSelect = document.getElementById('text_cols');
  const metaSelect = document.getElementById('meta_cols');
  if (!textSelect || !metaSelect) return;

  // Prevent selecting same column in both
  function syncSelections(source, target) {
    source.addEventListener('change', () => {
      const selected = Array.from(source.selectedOptions).map(o => o.value);
      Array.from(target.options).forEach(opt => {
        opt.disabled = selected.includes(opt.value);
      });
    });
    source.dispatchEvent(new Event('change'));
  }
  syncSelections(textSelect, metaSelect);
  syncSelections(metaSelect, textSelect);
});
