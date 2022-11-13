//MetaHandler
define([
    'jquery'
], function(
    $
) {
    'use strict';
    var metaHandler = {
        initialize: function(options) {
            this.$head = $('head');
            return this;
        },
        $: function(selector) {
            return this.$head.find(selector);
        },
        updateHead: function(attrs) {
            for(var key in attrs) {
                var val = attrs[key];
                if(key === 'title') {
                    this.$('title').text(val);
                } else if(key === 'meta') {
                    for(var i=0, l=val.length, metaItem ; i<l ; ++i) {
                        metaItem = val[i];
                        if(this.$('meta[name='+metaItem.name+']').length) {
                            this.$('meta[name='+metaItem.name+']').attr(metaItem);
                        } else {
                            this.$head.find('meta[charset]').after($('<meta/>', metaItem));
                        }
                    }
                } else if(key === 'removeMeta') {
                    for(var j=0, le=val.length, removeMetaItem; j<le ; ++j) {
                        removeMetaItem = val[j];
                        this.$('meta[name='+removeMetaItem.name+']').remove();
                    }
                }
            }
        }
    };
    return metaHandler;
});