// SearchView
define([
    'jquery',
    'backbone',
    'suiteio',
    'views/PagedListView'
],
function(
    $,
    Backbone,
    suiteio,
    PagedListView
    ) {
    'use strict';
    var SearchView = Backbone.View.extend({
        events: function() {
            return _.extend({
                // 'submit .navSearchForm': 'onSearchSubmit',
                'click .searchTab': 'filterChange',
                'click a[data-navigate]': 'linkCatcher'
            },
            _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function(options) {
            options = options || '';
            var self = this;
            this.shellTemplatePromise = suiteio.templateLoader.getTemplate('search-shell', ['search-related-tags', 'story-teaser', 'user-teaser', 'suite-mini-teaser']);            
            this.tagItemTmplPromise = suiteio.templateLoader.getTemplate('tag-list-item');
            this.setElement($('.searchNav'));

            this.currentQuery = options.query || '';
            this.filterType = options.filter || '';
            // this.rendering = $.Deferred();
            this.rootUrl = '/q/' + this.currentQuery;
            this.$('.searchTerm').on('keyup', function(e) { self.searchKeyHandler(e) });
            // this.setupFormEditor();
               
        },

        render: function(options) {
            options = options || {};
            var q = options.query;
            var self = this;

            this.$el.addClass('active');
            $('.searchNav').addClass('open');
            $('.searchNav').velocity('stop', true).velocity({ right: 0, width: 420 }, {
              duration: 140
            });    
            
            $('.closeSearch').velocity('stop', true).velocity({ rotateZ: -90 }, {
                duration: 30,
                delay: 20
            }); 

            $('.navSearchBody').velocity('stop', true).velocity({ bottom: 0 }, {
              duration: 140,
              easing: [ 0.035, 0.050, 1.000, -0.255 ]
            });            


            // $('.searchTerm').velocity('stop', true).velocity('transition.slideRightBigIn', 120);       
            // $('.navSearchBody').show().velocity('stop', true).velocity({ height: 'auto' }, {
            //   duration: 200,
            //   easing: [ 0.035, 0.050, 1.000, -0.255 ]
            // });        
            // $('.nsInner').velocity('stop', true).velocity({ opacity: 1, top: 0 }, {
            //   duration: 200,
            //   easing: [ 0.035, 0.050, 1.000, -0.255 ]
            // });             
            this.$('.searchTerm').focus();
            // this.fetchTrendingTags().then(function(tags){
            //     self.renderTrendingTags(tags.objects);
            // })            

            // $('.navbarFixedTop').not(self.$el).on('click', function() { self.closeNavSearch(); });
            $('.shell').on('click', function() { self.closeNavSearch(); });
            self.listenToOnce(suiteio.keyWatcher, 'keydown:27', self.closeNavSearch);

             $(document).off('.navSearchBody');
             $(document).on('DOMMouseScroll mousewheel', '.navSearchBody', function(ev) {
                var $this = $(this),
                    scrollTop = this.scrollTop,
                    scrollHeight = this.scrollHeight,
                    height = $this.height(),
                    delta = (ev.type == 'DOMMouseScroll' ?
                        ev.originalEvent.detail * -40 :
                        ev.originalEvent.wheelDelta),
                    up = delta > 0;

                var prevent = function() {
                    ev.stopPropagation();
                    ev.preventDefault();
                    ev.returnValue = false;
                    return false;
                }

                if (!up && -delta > scrollHeight - height - scrollTop) {
                    // Scrolling down, but this will take us past the bottom.
                    $this.scrollTop(scrollHeight);
                    return prevent();
                } else if (up && delta > scrollTop) {
                    // Scrolling up, but this will take us past the top.
                    $this.scrollTop(0);
                    return prevent();
                }
            });             

        },

        filterChange: function(e) {
            var self = this;
            this.changingFilters = true;
            e.preventDefault();
            var targetFilter = $(e.currentTarget).data('filter');
            if(targetFilter==this.filterType) {
                this.filterType = '';
            } else { this.filterType = $(e.currentTarget).data('filter'); }            
            this.currentQuery = this.$('.searchTerm').val();
            this.rootUrl = this.getSearchUrl(this.currentQuery, this.filterType);
            this.doSearch();
        },

        emptySearch: function() {
            this.$('.searchPreamble').addClass('empty');
        },

        // onSearchSubmit: function(e) {
        //     e.preventDefault();
        //     var query = $('.searchTerm').val() || '';
        //     query = query.toLowerCase().replace(/\s\s+/g, ' ').replace(/[^a-z\d\s]+/gi, "").trim().replace(/\s/ig, '-');
        //     if(query) {
        //         this.trigger('navSearchQuery', query);
        //     } 
        //     this.closeNavSearch();
        // },

        doSearch: function(e) {
            var self = this;
            var $html, context;
            var $resultsContainer = this.$('.searchResults');
            if(this.filterType) {
                this.setupSearchPaginator();
            } else {
                this.fetchContext().then(function(data) {
                    context = data;

                    self.shellTemplatePromise.done(function(tmpl) {
                        if(context.noResults) {
                            $html = 'nothing to see here';
                        } else {
                            $html = $(tmpl(context));                            
                        }
                        $resultsContainer.html($html);
                    });      
                });
            }
        },

        searchFormSubmit: function(e) {
            var self = this;
            this.changingFilters = true;
            e.preventDefault();
            this.currentQuery = $('.searchTerm').val() || '';
            this.rootUrl = this.getSearchUrl(this.currentQuery, this.filterType);
            if(this.currentQuery) {
                this.doSearch(e);
            }
        },        

        searchKeyHandler: function(e) {
            e.preventDefault();
            e.stopPropagation();            
            var self = this;
            var code = e.charCode || e.keyCode || e.which;
            var timeout = 700;

            if(code === 13) {
                e.preventDefault();
                this.searchFormSubmit(e);
                return;
            }            

            if (self.searchDoneTyping) {
                clearTimeout(self.searchDoneTyping);
            }
            if(code === 27) { return; }
            if(code <= 20 || code >=90) { return; }

            self.searchDoneTyping = setTimeout(function() { 
                self.searchFormSubmit(e);
                // self.doSearch(e);
            }, timeout);

        },

        getSearchUrl: function(query, filter) {
            var searchKey = '/q';
            var filterKey = '?filter=';
            query = query.toLowerCase().replace(/\s\s+/g, ' ').replace(/[^a-z\d\s]+/gi, "").trim().replace(/\s/ig, '-');
            if(!query) {
                return searchKey;
            } else {
                var url = searchKey + '/' + query;
                if(filter) {
                    url = url + filterKey + filter;
                }
                return url;
            }
        },

        fetchContext: function() {
            var self = this;
            return $.ajax({
                url: self.rootUrl,
                type: 'GET',
                data: {
                    spa: true,
                    filter: self.filterType
                }
            });
        },

        setupSearchPaginator: function() {
            var self = this;
            var $listViewEl = this.$('.searchResults');
            var $scrollerEl = this.$('.navSearchBody');
            var startPage = 1;
            var searchArr = window.location.search.split('=');
            var filterType = this.filterType || '';
            var template;
            var loadFirstPage = true;
            if(searchArr.length >= 2 && searchArr[0] === '?page') {
                startPage = +searchArr[1];
            }
            var url = this.rootUrl;
            switch(filterType) {
                case 'stories':
                    template = 'story-teaser';
                break;
                case 'suites':
                    template = 'suite-teaser';
                break;
                case 'people':
                    template = 'user-teaser';
                break;                    
            }

            this.searchListView && this.searchListView.destroy();
            this.searchListView = new PagedListView({
                firstPage: loadFirstPage,
                namedFilter: filterType,
                el: $listViewEl,
                scrollerEl: $scrollerEl,
                url: url,
                templateName: template,
                name: 'searchlistview'
            });
            this.listenTo(self.searchListView, 'listViewFiltered', function(namedFilter) {
                filterType = filterType || '';
                // if(namedFilter=='suite') {
                //     this.searchListView.templateName = 'suite-story-teaser';
                // } else if(namedFilter=='user') {
                //     this.searchListView.templateName = 'user-teaser';
                // }
                self.searchListView.fetch();
            });            
            this.listenToOnce(self.searchListView, 'listViewReady', function() {
                self.searchListView.fetch();
            });   
            self.listenToOnce(self.searchListView, 'noListViewResults', function() {
                self.$('.searchResults .paginatedList').html('');
            });                     
        },

        fetchTrendingTags: function() {
            var $tags = [];
            var url = '/lib/api/top_tags';
            var maxTags = 5;

            $tags = $.ajax({
                url: url,
                dataType : 'json',
                type: 'post',
                data: {
                    please: maxTags
                }
            });
            return $tags
        },

        renderTrendingTags: function(data) {
            var $tagContainer = $('.trendingTags');
            if(data && data.length) {
                this.tagItemTmplPromise.done(function(tmpl) {
                    var $domFrag = $(document.createDocumentFragment());
                    for(var i=0, l=data.length, tag ; i<l ; ++i) {
                        tag = data[i];
                        $domFrag.append(tmpl(tag));
                    }
                    $tagContainer.html($domFrag);
                });
            }
        },

        clearNavSearch: function() {
        },

        closeNavSearch: function() {
            $('.searchTerm').val('').blur();
            this.$el.removeClass('active');

            $('.searchNav').removeClass('open');
            // $('.searchNav').velocity('reverse');    
            $('.searchNav').velocity('stop', true).velocity({ right: 'intial', width: 42 }, {
              duration: 70
            });             
            $('.closeSearch').velocity('reverse');

            $('.navSearchBody').velocity('reverse');  

            // $('.searchNav').removeClass('open');
            // $('.navSearchBody').velocity('stop', true).velocity({ height: 0 }, {
            //   duration: 200,
            //   easing: [ 0.19, 1, 0.22, 1 ]
            // }).hide();        
            // $('.nsInner').velocity('stop', true).velocity({ opacity: 0, top: -64 }, {
            //   duration: 200,
            //   easing: [ 0.19, 1, 0.22, 1 ]
            // });   

            this.stopListening(suiteio.keyWatcher);
            $('.shell').off('click'); // Also unbind the shell click
            $('.searchResults').html('');
            this.trigger('searchClosed');
        },

        linkCatcher: function() {
            this.closeNavSearch();
        },

        destroy: function() {
            this.searchListView && this.searchListView.destroy();
            Backbone.View.prototype.destroy.apply(this, arguments);
            this.unbind();
            this.stopListening();;
        }
    });
    return SearchView;
});