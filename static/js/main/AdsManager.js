//AdManager.js
define([
    'jquery',
    'main/ads'
], function($, ads) {
    'use strict';
    var googletag = window.googletag;
    var AdsManager = {
        initialize: function(options) {
            this.ads = ads;
            this.initialized = true;
            this.$el = $(options.el) || $('body');
            this.$ = function() {
                return this.$el.find.apply(this.$el, arguments);
            }
        },
        loadDfp: function() {
            console.log('Hello loadDfp function');
            if(!googletag) { return; }
            var gcmd = googletag.cmd,
                displays = [];
            for(var idx=0, len=this.ads.dfps.length ; idx<len ; ++idx) {
                var tempAd = this.ads.dfps[idx];
                //only load and draw ads if the corresponding div#id element exists on page
                gcmd.push(function() {
                    googletag.defineSlot(tempAd.unitName, tempAd.size, tempAd.id).addService(googletag.pubads());
                });
                displays.push(tempAd);
                // }
            }
            gcmd.push(function() {
                googletag.pubads().enableSingleRequest();
                googletag.enableServices();
            });
            for(var idxd=0, lend=displays.length; idxd<lend; ++idxd) {
                if (!displays[idxd].ajax) {
                    if(this.$('#'+displays[idxd].id).filter(':visible').length ) {
                        //console.log(displays[idxd].id + 'firing!');
                        gcmd.push(function() {
                            googletag.display(displays[idxd].id);
                        });
                    }
                } else {
                    // console.log(displays[idxd].id + ' is not visible');
                }
            }
        },
        loadSingleDfp: function(id) {
            if(!this.initialized) {
                this.initialize({});
            }
            var gcmd = window.googletag.cmd, dfps = this.ads.dfps;
            for(var idxd=0, lend=dfps.length; idxd<lend; ++idxd) {
                if (dfps[idxd].id === id) {
                    if(this.$('#'+dfps[idxd].id).filter(':visible').length ) {
                        // console.log(dfps[idxd].id + 'firing!');
                        gcmd.push(function() {
                            googletag.display(dfps[idxd].id);
                        });
                    } else {
                        // console.log(dfps[idxd].id + ' is not visible');
                    }
                    break;
                }
            }
        },
        loadContentAd: function() {
            //content.ad stuffs
            var $contentad = this.$('.contentad18648');
            if(!$contentad.length || !$contentad.is(':empty') || $contentad.css('display') === 'none') {
                // console.log('not loading contentad again');
                return;
            }
            var params =
            {
                id: "8997391c-cf36-4e1a-b75a-a02ec0695fa5",
                d:  "c3VpdGUuaW8=",
                wid: "18648",
                cb: (new Date()).getTime()
            };
            var qs="";
            for(var key in params){qs+=key+"="+params[key]+"&"}
            qs=qs.substring(0,qs.length-1);
            var s = document.createElement("script");
            s.type= 'text/javascript';
            s.src = "//api.content.ad/Scripts/widget.aspx?" + qs;
            s.async = true;
            $contentad.get(0).appendChild(s);
        },
        loadAdsense: function() {
            if(this.$('.gasBottom').length) {
                // console.log('adsense bottom');
                (adsbygoogle = window.adsbygoogle || []).push({});
            }
            if(this.$('.gasIn').length) {
                // console.log('adsense in');                
                (adsbygoogle = window.adsbygoogle || []).push({});
            }
            if(this.$('.gasLeft').length) {
                // console.log('adsense in');                
                (adsbygoogle = window.adsbygoogle || []).push({});
            }
            if(this.$('.gasTop').length) {
                // console.log('adsense top');                
                (adsbygoogle = window.adsbygoogle || []).push({});
            }
        },
        destroy: function() {
            this.$el = null;
            this.initialized = false;
        }
    };
    return AdsManager;
});