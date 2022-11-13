define(['jquery'], function($) {
    'use strict';
    var defaults = {};
    var FONT_ASPECT_RATIO = .45; // font width / font height
    var autoExpandTextarea = {
        initialize: function(options) {
            var $textarea = this,
                twidth = $textarea.width(),
                fontSize = parseInt($textarea.css('font-size').replace('px', ''), 10), //font height
                fontWidth = fontSize * FONT_ASPECT_RATIO,
                lineHeight = parseInt($textarea.css('line-height').replace('px', ''), 10),
                verticalPadding = parseInt($textarea.css('padding-top').replace('px', ''), 10) + parseInt($textarea.css('padding-bottom').replace('px', ''), 10),
                charPerLine = .95 * twidth / fontWidth;
            $textarea.css({
                'resize': 'none',
                'overflow': 'hidden'
            });
            autoExpandTextarea.destroy.apply(this);//make sure we're not binding it twice
            this.data('autoExpandOn', true);
            this.on('keyup.autoExpand', function (e) {
                //scrollbar is showing
                var code = e.charCode || e.keyCode || e.which,
                    chr = String.fromCharCode(code);
                if (code === 8 || code === 13 || chr.match(/[0-9a-z-_#]/ig)) {
                    window.setTimeout(function() {
                        resize(code);
                    }, 200);
                }
            });
            function resize() {
                var charLength = $textarea.val().length;
                if(!charLength) {
                    charLength = 1;
                }
                var returns = $textarea.val().match(/\n/ig),
                    lines = Math.ceil(charLength/charPerLine);
                if(returns) {
                    lines += returns.length;
                }
                var newHeight = (lines * lineHeight) + verticalPadding;
                if($textarea.height() !== newHeight) {
                    $textarea.css('height', newHeight);
                }
            }
            resize();
        },
        destroy: function() {
            this.off('.autoExpand');
            this.data('autoExpandOn', null);
        }
    };
    $.fn.autoExpandTextarea = function(method) {
        var options = {};
        if(!method || typeof method==='object') {
            $.extend(options, defaults, method);
            for(var i=0,l=this.length ; i<l ; ++i) {
                if(this.get(0).tagName !== 'TEXTAREA') {
                    continue;
                }
                autoExpandTextarea.initialize.call(this.eq(i), options);
            }
            return this;
        } else if(autoExpandTextarea[method] && typeof autoExpandTextarea[method] === 'function') {
            for(var j=0,ll=this.length ; j<ll ; ++j) {
                autoExpandTextarea[method].apply(this.eq(j), arguments);
            }
            return this;
        }
    };
    //jQuery plugin, no exports
});