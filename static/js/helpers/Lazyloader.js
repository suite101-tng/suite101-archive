/*globals define*/
define(['jquery', 'underscore'], function($, _) {
    'use strict';
    var Lazyloader = function(options) {
        var self = this,
            _options = {};
        this.options = _options = $.extend({
            url: '.',
            dataType: 'text'
        }, options);
        if (_options.pageNo === undefined) {
            this.pageNo = 1;
        } else {
            this.pageNo = _options.pageNo;
        }
        this.startingPageNo = this.pageNo;
        this.suspended = false;
        this.pageCache = [];
        this.reachedBottom = false;
        this.renderRepeatCount = 0;
        this.scrollWatch = this.options.scrollWatch || $(window);
        if(_options.manual) {

        } else if(this.pageNo !== 0) {
            this.bindScroll();
        }
    };
    
    Lazyloader.prototype.bindScroll = function() {
        var self = this;
        this.detectScroll(); //run it once manually, in case the scroll container requires no scroll i.e. big screen
        $(this.scrollWatch).off('scroll.lazyload'+this.options.id).on('scroll.lazyload'+this.options.id, _.debounce(function(){
            self.detectScroll();
        }, this.options.delay));
    };
    
    Lazyloader.prototype.suspend = function() {
        this.suspended = true;
        $(this.scrollWatch).off('scroll.lazyload'+this.options.id);
    };
    
    Lazyloader.prototype.resume = function() {
        this.suspended = false;
        if(!this.options.manual) {
            this.bindScroll();
        }
    };
    
    Lazyloader.prototype.getPageNo = function() {
        return this.pageNo;
    };
    
    Lazyloader.prototype.incrementPageNo = function() {
        this.pageNo++;
    };
    
    Lazyloader.prototype.detectScroll = function() {
        var scrollTop = $(this.scrollWatch).scrollTop(),
            apex;
        if(this.options.semiautomatic && this.getPageNo() > (this.startingPageNo + 1)) {
            return;
        }
        try {

            if(!this.options.scrollWatch) {
                apex = ($(this.options.contentContainer).outerHeight(true) + $(this.options.contentContainer).offset().top) - $(window).outerHeight(true) - this.options.threshold;
                if(scrollTop >= apex) {
                    this.renderNextPage();
                }
            } else {
                if(this.options.scrollUp) {
                    apex = $(this.options.scrollWatch).scrollTop() + this.options.threshold;
                    if(apex <= this.options.threshold) {
                        this.renderNextPage();
                    }
                } else {
                    apex = $(this.options.scrollWatch).scrollTop() + $(this.options.scrollWatch).outerHeight() + this.options.threshold;
                    if(apex >= $(this.options.contentContainer).outerHeight()) {
                        this.renderNextPage();
                    }
                }
            }
        } catch(e) {
        }
    };
    Lazyloader.prototype.getNextPage = function() {
        if(this.reachedBottom) {
            return;
        }
        var currentPage = this.getPageNo(),
            nextPage = currentPage + 1,
            self = this;
        // debugger;
        return $.ajax({
            url: this.options.url,
            type: 'GET',
            dataType: this.options.dataType,
            data: $.extend({
                page: nextPage
            }, this.options.data, {lzldr: 1}),
            success: function(response) {
                if(!self.pageCache) {
                    //lazyloader destroyed, just return
                    return;
                }
                if(response) {
                    self.pageCache.push(response);
                    self.incrementPageNo();
                    if (self.getPageNo() === 1){
                        self.renderNextPage();
                        self.bindScroll();
                    }
                    // if(self.options.expectLoadMore && !response.match(/class="loadMore"/)) {
                    //     self.reachedBottom = true;
                    //     self.suspend();
                    // }
                } else {
                    self.reachedBottom = true;
                    self.onReachedBottom();
                    self.suspend();
                }
                if(self.options.success && typeof self.options.success === 'function') {
                    self.options.success.apply(self, arguments);
                }
            },
            error: function(response, status, error_msg) {
                if(self.options.error && typeof self.options.error === 'function') {
                    self.options.error.apply(self, arguments);
                }
                if(error_msg === 'NOT FOUND') {
                    self.reachedBottom = true;
                    self.onReachedBottom();
                }
            }
        });
    };
    
    Lazyloader.prototype.onReachedBottom = function() {
        var context = this.options.renderContext || this;
        if(this.options.bottomedCallback && typeof this.options.bottomedCallback === 'function') {
            this.options.bottomedCallback.call(context);
        }
    };

    Lazyloader.prototype.setUrl = function(url) {
        this.url = url;
    };
    
    Lazyloader.prototype.renderNextPage = function(doneCallback) {
        this.getNextPage();
        var self = this;

        if(!$(this.options.contentContainer).filter(':visible').length) {
            return;
        }
        if(this.renderTimerID) {
            //clear timer if it exists
            this.renderRepeatCount += 1;
            window.clearTimeout(this.renderTimerID);
        }
        if(this.getPageNo() > (this.startingPageNo) && this.options.semiautomatic) {
            //with semi automatic mode, we stop watching scrolls after page this.startingPageNo
            if(!this.suspended) {
                this.suspend();
            }
        }
        if(this.pageCache && this.pageCache.length>0) {
            //pageCache has pages not yet rendered
            //reset counter
            this.renderRepeatCount = 0;
            var renderContext = this.options.renderContext || this;
            if(this.options.render && typeof this.options.render === 'function') {
                this.options.render.call(renderContext, this.pageCache.pop());
            }
            if(doneCallback && typeof doneCallback === 'function') {
                doneCallback.call(renderContext);
            }
            this.getNextPage();
        } else {
            //if pageCache is empty, check again in 500ms
            if(this.renderRepeatCount <= 5) {
                this.renderTimerID = window.setTimeout(function() {
                    self.renderNextPage(doneCallback);
                }, 500);
            } else {
                //reset counter
                this.renderRepeatCount = 0;
                this.reachedBottom = true;
                this.onReachedBottom();
            }
        }
    };
    Lazyloader.prototype.destroy = function() {
        this.pageCache = [];
        if(this.renderTimerID) {
            //clear timer if it exists
            window.clearTimeout(this.renderTimerID);
        }
        $(this.scrollWatch).off('.lazyload'+this.options.id);
    };
    return Lazyloader;
});