(() => {
    const rtePurify = DOMPurify();
    const rtePurifyConfig = { SANITIZE_NAMED_PROPS: true };
  
    rtePurify.addHook('uponSanitizeElement', (node, data) => {
      if (data.tagName === 'span' && node.classList.contains('ql-formula')) {
        node.innerText = `$${node.dataset.value}$`;
      }
    });
  
    window.PLRTE = function (uuid, options) {
      if (!options.modules) options.modules = {};
      if (options.readOnly) {
        options.modules.toolbar = false;
      } else {
        options.modules.toolbar = [
          [{ script: 'sub' }, { script: 'super' }],
          ['clean'],
        ];
      }
  
      options.modules.keyboard = {
        bindings: {
          tab: {
            key: 9,
            handler: () => {
              return true;
            },
          },
          superscript: {
            key: 38,
            altKey: true,
            handler: (range, context) => {
                console.log(context);
                quill.format('script', 'super');
            },
          },
          subscript: {
            key: 40,
            altKey: true,
            handler: (range, context) => {
                console.log(context);
                quill.format('script', 'sub');
            },
          },
          clearFormat: {
            key: 220,
            altKey: true,
            handler: function (range, context) {
                if (!range) return;
                if (range.length === 0) {
                    const currentScript = context.format.script;
                    if (currentScript) {
                        quill.format('script', false);
                    }
                } else {
                    quill.removeFormat(range.index, range.length);
                }
                console.log("Cleared formatting for range:", range);
            },
        },
        },
      };
  
      let inputElement = $('#rte-input-' + uuid);
      let quill = new Quill('#rte-' + uuid, options);
      let renderer = null;
      if (options.format === 'markdown') {
        renderer = new showdown.Converter({
          literalMidWordUnderscores: true,
          literalMidWordAsterisks: true,
        });
      }
  
      if (options.markdownShortcuts && !options.readOnly) new QuillMarkdown(quill, {});
  
      let contents = atob(inputElement.val());
      if (contents && renderer) contents = renderer.makeHtml(contents);
      contents = rtePurify.sanitize(contents, rtePurifyConfig);
  
      quill.setContents(quill.clipboard.convert({ html: contents }));
  
      const getText = () => quill.getText();
  
      quill.on('text-change', function () {
        let contents = quill.editor?.isBlank?.()
          ? ''
          : rtePurify.sanitize(quill.getSemanticHTML(), rtePurifyConfig);
        if (contents && renderer) contents = renderer.makeMarkdown(contents);
        inputElement.val(
          btoa(
            he.encode(contents, {
              allowUnsafeSymbols: true, 
              useNamedReferences: true,
            }),
          ),
        );
  
      });
      $('#rte-help-btn-' + uuid).on('click', function () {
        $('#rte-help-modal-' + uuid).modal('show');
      });

      $('#rte-help-close-' + uuid).on('click', function () {
          $('#rte-help-modal-' + uuid).modal('hide');
      });
    };
  
  
    var Embed = Quill.import('blots/embed');
  
    class MathFormula extends Embed {
      static create(value) {
        const node = super.create(value);
        if (typeof value === 'string') {
          this.updateNode(node, value);
        }
        return node;
      }
  
      static updateNode(node, value) {
        MathJax.startup.promise.then(async () => {
          const html = await (MathJax.tex2chtmlPromise || MathJax.tex2svgPromise)(value);
          const formatted = html.innerHTML;
          node.innerHTML = formatted + '&#8201;';
          node.contentEditable = 'false';
          node.setAttribute('data-value', value);
        });
      }
  
      static value(domNode) {
        return domNode.getAttribute('data-value');
      }
    }
    MathFormula.blotName = 'formula';
    MathFormula.className = 'ql-formula';
    MathFormula.tagName = 'SPAN';
  
    Quill.register('formats/formula', MathFormula, true);
  })();