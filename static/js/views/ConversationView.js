//ConversationView.js
define([
    'jquery',
    'backbone',
    'underscore',
    'suiteio',
    'lib/underwood',    
    'views/PagedListView'
], function(
    $,
    Backbone,
    _,
    suiteio,
    Underwood,
    PagedListView
) {
    'use strict';
    var ConversationView = Backbone.View.extend({

        events: function() {
            return _.extend({
                'click .suiteSelector': 'toggleStorySuite',
                'click .articleBody figure.plain': 'toggleZoomImage',
                'click .dateTime': 'toggleDates',
                'click .storyPermalink': 'selectPermalink',                               
                'click .ownProvider': 'userGo',
                'click .storyTeaserBody': 'toggleFullTeaser'
            }, _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function(options) {
            var self = this;
            this.templateName = 'conversation-detail';
            this.needForceRender = false;
            this.ownerViewing = false;

            // if(suiteio.getWindowSize().width < 768) {
            //     this.smallScreen = true; } else { this.smallScreen = false; }

            this.model = options.model || null;
            this.editing = false;

            if(!this.model) { //SPA, expect model to sync
                console.log('we do not have a bootstrapped model here...');
                this.listenToOnce(this.model, 'sync', function() {
                    self.ownerViewing = !!(suiteio.loggedInUser && (suiteio.loggedInUser.id == self.model.get('author').id));
                    self.render();
                });
            } else {
                var $el = $('.pageContainer#conv-'+this.model.id);
                if($el.length) {
                    console.log('we have an element!');
                    this.setElement($el);
                    this.afterRender();
                } else {
                    this.needForceRender = true;
                }                
            }

            this.isMod = suiteio.loggedInUser && suiteio.loggedInUser.get('isModerator');          

            this.listenTo(suiteio.vent, 'miniStoryCreated', function() {
                // console.log('ConversationView heard miniStoryCreated from the event bus');
                // add it to story.responses
            });
            
            this.listenTo(suiteio.vent, 'storySuitesUpdated', function(storyId, suites) {
                if(storyId == this.model.id) {
                    var otherSuitesCount = 0;
                    if(suites.length > 1) {
                        otherSuitesCount = suites.length
                    }
                    this.model.set(_.extend({
                        suites: suites,
                        otherSuitesCount: otherSuitesCount
                    }));
                }
            });

            this.listenTo(this.model.postsCollection, 'add', function(postsToAdd, backwardPageLoad) {
                backwardPageLoad = backwardPageLoad || false;
                if(backwardPageLoad) {
                    this._renderOldMessages(postsToAdd, true);
                } else {
                    this.renderItems(postsToAdd);
                }
            });            

            this.templatePromise = suiteio.templateLoader.getTemplate(this.templateName, [
                'post-detail',
                'story-embed',
                'tag-list-item'
            ]);            
        },

        render: function() {
            var self = this;
            this.templatePromise.done(function(tmpl) {
                var contextMixin = {
                    clientSideRender: true,
                    userLoggedIn: !!(suiteio.loggedInUser && (suiteio.loggedInUser.id)),
                    ownerViewing: self.ownerViewing,
                    isMod: self.isMod
                },
                    context = {},
                    $html,
                    $el;
                if(suiteio.loggedInUser) {
                    contextMixin.loggedInUser = suiteio.loggedInUser.toJSON();
                }
                context = $.extend(contextMixin, self.model.toJSON());
                $html = $(tmpl(context));
                if($html.length > 1) {
                    $el = $('<div/>').append($html);
                } else {
                    $el = $html.eq(0);
                }
                if(self.$el.is(':empty')) {
                    //first time render
                    self.setElement($el);
                } else {
                    self.$el.html($html.html());
                }
                self.trigger('renderComplete', self.$el);
                self.needForceRender = false;
            });
        },

        afterRender: function() {
            var self = this;
            this.$('.tip').tooltip();
            // this.setupRelatedPosts();

            // setup main create form
            var wait = setTimeout(function() {   
                self.trigger('setupMainPostForm', self.$('.mainPostForm'), self.model);
            }, 500);
            
            // this.sendGaView();
         },

        openGutter: function(e) {
            // 1 get target id
            // 2 get related (child) discussions
            // 3 open up the gutter
            this.$('.convStem').velocity('stop', true).velocity({ left: -420 }, {
              duration: 140,
              easing: [ 0.035, 0.050, 1.000, -0.255 ]
            });
        },

        loadNewPosts: function() {
            this.model.getLatestPosts();        
        },

        // setupRelatedPosts: function() {
        //     var self = this;
        //     var $listViewEl = this.$('.nextRelated');
        //     var url = '/a/api/related/' + this.model.id;
        //     // if(this.storyRelatedList) {
        //     //     this.storyRelatedList && this.storyRelatedList.destroy();
        //     // }
        //     self.storyRelatedList = new PagedListView({
        //             firstPage: true,
        //             el: $listViewEl,
        //             url: url,
        //             templateName: 'story-teaser',
        //             name: 'story-list-' + self.model.id
        //     });
        //     self.listenTo(self.storyRelatedList, 'listViewFiltered', function(namedFilter) {
        //         namedFilter = namedFilter || '';
        //         self.storyRelatedList.fetch();
        //     });                     
        //     self.listenToOnce(self.storyRelatedList, 'listViewReady', function() {
        //         self.storyRelatedList.fetch();
        //     });
        //     self.listenToOnce(self.storyRelatedList, 'errorFetchingCollection' || 'noListViewResults', function() {
        //         self.$('.mySuites .paginatedList').html('');
        //     });
        // },

        modAction: function(e) {
            suiteio.pageController.modThis(e);
        },

        toggleDates: function(e) {
            this.$('.dateTime').toggleClass('mod');
        },

        selectPermalink: function(e) {
            e.preventDefault();
            e.stopPropagation();
            var permalink = this.$('.storyPermalink .link');
            permalink.select();
        },

        userGo: function(e) {
            e.preventDefault;
            var $slug = $(e.currentTarget).data('slug').substring(1);
            this.trigger('goToUser', $slug);
        },

        imageZoomOut: function(id) {
            var $figure = this.$('figure[data-id='+id+']'),
                $figcaption = $figure.find('figcaption'),
                $img = $figure.find('img'),
                self = this,
                _3dTransform = 'translate3D(0,0,0)',
                scaleTransform = 'scale(1)',
                $scrim = $('body').find('.scrim');
                $('body').removeClass('image-zoomed-in');
            $scrim.off().remove();
            $figcaption.css({
                '-webkit-transform': _3dTransform,
                '-moz-transform': _3dTransform,
                '-ms-transform': _3dTransform,
                '-o-transform': _3dTransform,
                'transform': _3dTransform
            });
            $img.closest('.zoomWrapper').css({
                '-webkit-transform': _3dTransform,
                '-moz-transform': _3dTransform,
                '-ms-transform': _3dTransform,
                '-o-transform': _3dTransform,
                'transform': _3dTransform
            });
            $img.removeClass('zoomedIn zoomed-in').css({
                '-webkit-transform': scaleTransform,
                '-moz-transform': scaleTransform,
                '-ms-transform': scaleTransform,
                '-o-transform': scaleTransform,
                'transform': scaleTransform
            });
            if(this.zoomintimer) {
                clearTimeout(this.zoomintimer);
            }
            this.zoomouttimer = setTimeout(function() {
                if($img.parent('.zoomWrapper').length) {
                    $img.unwrap();
                }
                this.zoomouttimer = null;
            }, 200);
        },

        imageZoomIn: function(id) {
            var $figure = this.$('figure[data-id='+id+']'),
                $img = $figure.find('img'),
                $figcaption = $figure.find('figcaption'),
                self = this,
                $scrim = $('body').find('.scrim'),
                dataWidth = $img.data('width'),
                displayWidth = $img.outerWidth(),
                displayHeight = $img.outerHeight(),
                imgOffsetTop = $img.offset().top,
                imgOffsetLeft = $img.offset().left,
                windowWidth = $(window).outerWidth(),
                windowHeight = $(window).outerHeight(),
                windowAspectRatio = windowWidth / windowHeight,
                aspectratio = displayWidth / displayHeight,
                newHeight = 0,
                newWidth = 0,
                scale = 1,
                _3dTransform = '',
                scaleTransform = '',
                $zoomWrapper = $('<div/>', {
                    'class': 'zoom-wrapper zoomWrapper'
                });
            if($('html').hasClass('touch') || windowWidth < 600 || windowHeight < 300) {
                return;
            }
            if(dataWidth < 400) {
                newHeight = displayHeight;
                newWidth = displayWidth;
                scale = 1;
            } else if(displayHeight > windowHeight || windowAspectRatio > aspectratio) {
                newHeight = windowHeight * 0.8;
                newWidth = newHeight * aspectratio;
                scale = newHeight / displayHeight;
            } else {
                newWidth = windowWidth * 0.8;
                newHeight = newWidth / aspectratio;
                scale = newWidth/displayWidth;
            }
            $figure.find('img, figcaption').wrapAll($zoomWrapper);
            $(window).off('.zoomscrollwatch').on('scroll.zoomscrollwatch', _.debounce(function() {
                self.imageZoomOut(id);
            }, 150));
            if(this.zoomouttimer) {
                clearTimeout(this.zoomouttimer);
            }
            $(document).off('.zoomscrollwatch').on('keydown.zoomscrollwatch', function() {
                self.imageZoomOut(id);
            });
            this.zoomintimer = setTimeout(function() {
                this.zoomintimer = null;
                var newTop = 0, newLeft = 0;
                // if(scale === 1 && displayWidth < 400) {
                newLeft = (-1 * imgOffsetLeft) + ((windowWidth - displayWidth) / 2);
                newTop = $(window).scrollTop() + (-1 * imgOffsetTop) + ((windowHeight - displayHeight) / 2);
                // } else {
                    // newTop = ((-1 * imgOffsetTop) + (windowHeight*0.1) + ((newHeight - displayHeight)/2));
                // }
                _3dTransform = 'translate3D(' + newLeft + 'px ,'+ newTop + 'px, 0px)';
                scaleTransform = 'scale('+scale+')';
                $figcaption.show().css({
                    '-webkit-transform': 'translate3D(0px, '+ ((newHeight-displayHeight)/2) +'px, 0px)',
                    '-moz-transform': 'translate3D(0px, '+ ((newHeight-displayHeight)/2) +'px, 0px)',
                    '-ms-transform': 'translate3D(0px, '+ ((newHeight-displayHeight)/2) +'px, 0px)',
                    '-o-transform': 'translate3D(0px, '+ ((newHeight-displayHeight)/2) +'px, 0px)',
                    'transform': 'translate3D(0px, '+ ((newHeight-displayHeight)/2) +'px, 0px)'
                });
                $img.closest('.zoomWrapper').css({
                    '-webkit-transform': _3dTransform,
                    '-moz-transform': _3dTransform,
                    '-ms-transform': _3dTransform,
                    '-o-transform': _3dTransform,
                    'transform': _3dTransform
                });
                $img.addClass('zoomedIn zoomed-in').css({
                    '-webkit-transform': scaleTransform,
                    '-moz-transform': scaleTransform,
                    '-ms-transform': scaleTransform,
                    '-o-transform': scaleTransform,
                    'transform': scaleTransform
                });
                if(!$scrim.length) {
                    $scrim = $('<div/>', {'class': 'scrim'}).insertBefore($figure);
                    $scrim.on('click.zoomscrollwatch', function() {
                        self.imageZoomOut(id);
                    });
                }
            }, 0);
            $('body').addClass('image-zoomed-in');
        },

        toggleZoomImage: function(e) {
            var $figure = $(e.currentTarget),
                $img = $figure.find('img'),
                id = $figure.data('id');
            if(id) {
                if($img.hasClass('zoomedIn zoomed-in')) {
                    this.imageZoomOut(id);
                } else {
                    this.imageZoomIn(id);
                }
            }
        },

        toggleCaption: function(e) {
            var $container = $('.featureImage');
            $container.toggleClass('open-caption');
            $(document).off('.featureImage').on('click.featureImage keyup.featureImage', function(e) {
                if(e.type === 'keyup') {
                    var code = e.charCode || e.keyCode || e.which;
                    if(code === 27) {
                        $container.removeClass('open-caption');
                    }
                } else if(e.type === 'click') {
                    $container.removeClass('open-caption');
                }
            });


        },

        sendGaView: function() {
            var authGa, storyPage, storyTitle;
            var activeModel = this.model;
            var ref = this.model && this.model.get('ref');
            if(ref) {
               authGa = ref.gaCode;
               storyPage = ref.link || '';
               storyTitle = ref.title || '';
            } else {
                console.log('get fields from model');
                authGa = this.model && this.model.get('author').gaCode;
                storyPage = this.model.get('absoluteUrl');
                storyTitle = this.model.get('title');
            }
            if(authGa) {
                try {
                    ga('create', authGa, 'auto', {'name': 'newTracker'});  // New tracker.
                    console.log(storyTitle);
                    ga('newTracker.send', 'pageview', {
                        'cookieDomain': 'none',
                        'page': storyPage,
                        'title': storyTitle
                    });
                } catch(e) {
                    console.log(e);
                }
            }
        },
        
        followSuite: function(e) {
            suiteio.followSuite(e);
        },

        followUser: function(e) {
            suiteio.followUser(e);
        },

        editArticleAction: function() {
            this.trigger('openEditMode', this.model);
            this.editing = true;
        },

        publishStory: function(e) {
            var self = this;
            // this.trigger('publishThisStory', this.model);
            var $publishButt = self.$('.publishStory');
            $publishButt.dynamicButton({immediateEnable: true});
            this.model.set(_.extend({
                status: 'published'
            })).save().done(function(){
                self.render();
            })
        },

        loginModal: function() {
            suiteio.fireLoginModal();
        },
   
        openSuiteSelector: function(e) {
            suiteio.openSuiteSelector(e, this.create);
        },

        flagStory: function(e) {
            suiteio.flagIt(e);
        },       

        toggleFullTeaser: function(e) {
            suiteio.toggleFullTeaser(e);
        },        

        ////// TODO: get selected text, use in tweet, share, etc
        // shareFromSelection: function() {
        //     var html = "";
        //     if (typeof window.getSelection != "undefined") {
        //         var sel = window.getSelection();
        //         if (sel.rangeCount) {
        //             var container = document.createElement("div");
        //             for (var i = 0, len = sel.rangeCount; i < len; ++i) {
        //                 container.appendChild(sel.getRangeAt(i).cloneContents());
        //             }
        //             html = container.innerHTML;
        //         }
        //     } else if (typeof document.selection != "undefined") {
        //         if (document.selection.type == "Text") {
        //             html = document.selection.createRange().htmlText;
        //         }
        //     }
        //     return html;
        // },

        destroy: function() {
            $(window).off('scroll.scrollDepth');
            $(window).off( "resize" );  
            this.pagedResponseList && this.pagedResponseList.destroy();
            Backbone.View.prototype.destroy.apply(this, arguments);
        }

    });
    return ConversationView;
});