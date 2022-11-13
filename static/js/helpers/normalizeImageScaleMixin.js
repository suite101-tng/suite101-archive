/*globals define*/
define([], function() {
    'use strict';
    var normalizeImageScale = function($imageWrapper, baseWidth) {
        var wrapperWidth = $imageWrapper.width(),
            $img = $imageWrapper.find('img'),
            ratio = 1,
            w = $img.data('scaledWidth') && parseInt($img.data('scaledWidth'), 10),
            top = $img.data('topPosition') && parseInt($img.data('topPosition'), 10),
            //wo = parseInt($img.data('originalWidth')),
            scale = $img.data('scale') || 1,
            left = $img.data('leftPosition') && parseInt($img.data('leftPosition'), 10),
            cssData = {};
        // if(wrapperWidth != baseWidth) {
            ratio = baseWidth/wrapperWidth;
            if (w) cssData.width = Math.round(w / ratio);
            if (top) cssData.top = Math.round(top / ratio);
            if (left) cssData.left = Math.round(left / ratio);
            $img.css(cssData);
            $img.data('vpScaledOrigWidth', Math.round(w/ratio) / scale);
            $img.data('viewPortRatio', ratio);
        // }
        return true;
    };
    return normalizeImageScale;
});