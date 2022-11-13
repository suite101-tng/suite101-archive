define([
    'jquery',
    'suiteio',
    'backbone',
    'underscore',
    'lib/highstock',
    'views/PagedListView',
    'moment'
],
function(
    $,
    suiteio,
    Backbone,
    _,
    Highcharts,
    PagedListView,
    moment
) {
    'use strict';
    var StatsView = Backbone.View.extend({       
        events: function() {
            return _.extend({
                'click .rangeItem': 'updateRange',
                'click .resetZoom': 'resetZoom',
                'click .showStoryStats': 'showSecondaryStatsPane',
                'click .secondaryPaneBeGone': 'secondaryPaneBeGone',
                'click .seriesItem': 'onStatsSectionChange',                
                'click .sumBlock': 'toggleSeriesActive'
            }, _.result(Backbone.View.prototype, 'events'));
        },

        initialize: function () {
            var self = this;
            // this.$el = $('.notifsContainer');
            // this.setElement($('.notifsContainer'));
            this.statsTmplPromise = suiteio.templateLoader.getTemplate('stats-shell');
            this.render();

            // this.chartData = new Backbone.Model();

            this.width = 32;

            this.statsSummaryTmpl = suiteio.templateLoader.getTemplate('stats-summary');
            this.storyMiniTeaserTmpl = suiteio.templateLoader.getTemplate('stats-mini-story');
            this.contentStatsTmpl = suiteio.templateLoader.getTemplate('content-stats',['story-teaser','suite-teaser']);            

            this.userTeaserTmpl = suiteio.templateLoader.getTemplate('user-teaser');

            this.showstories = true;
            this.showpageviews = true;

            this.currentTarget = 'posts';
            this.contentId = ''; // target for secondary stats pane
            this.timePeriod = 30 // default period
            this.url = '/stats';


            var $el = $('#stats-view');
            // $el.find('.tip').tooltip('destroy').tooltip();
            if($el.length) {
                this.setElement($el);
                this.trigger('renderComplete');
            } else {
                this.render();
            }
        },

        render: function() {
            var self = this;
            var $el;
            var $html;
            self.statsTmplPromise.done(function(tmpl) {
                $html = $(tmpl({
                }));
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
                // self.trigger('renderComplete', self.$el);
        
            });      
            self.fetchFreshData().then(function(data) {
                self.chartData = new Backbone.Model(data.chartdata);
                console.log(data);
                self.renderStatsSummary(data.summary);
                self.trigger('renderComplete', self.$el);
            });
        },

        loadChart: function() {
            var self = this;

            self.highchartIt();    
            self.$('.royDetail').tooltip();

            // (function (H) {
            //     H.wrap(H.Tooltip.prototype, 'hide', function () {});
            // }(Highcharts));

            self.loadStoryPaginator();
            self.listenTo(self.chartData, 'change', function() {
                self.updateChartSeries(self.currentTarget);
            });
        },

        fetchFreshData: function() {
            var $target = this.currentTarget;
            var $period = this.timePeriod;
            var contentId = this.contentId;
            var self = this;
            var url = self.url;
           
            var freshData = $.ajax({
                url: url,
                type: 'POST',
                dataType: 'json',
                data: {
                    contentid: contentId,
                    timeperiod: $period,
                    target: $target
                },
            });
            return freshData;
        },

        deactivateSeries: function(seriesName) {
            var seriesId = seriesName + '-series';            
            var defaults = getSeriesOptions(seriesName);
            var series = this.chart.get(seriesId);

            series.options.color = defaults.color;
            series.options.marker = { enabled: false, states: { hover: { enabled: false }} };                        
            series.options.shadow = false;                        
            series.options.lineWidth = defaults.lineWidth;
            series.update(series.options);
        },

        toggleSeriesActive: function(e) {
            var self = this;
            var $target = $(e.currentTarget);
            var series = $target.data('series');
            var seriesId = series + '-series';
            var activeColors = ['rgba(255,255,255,.9', '#1a8bba', '#39c6bf', '#d63020']
            if(series == this.activeSeries) {
                this.deactivateSeries(series);
                this.activeSeries=null;
                $target.removeClass('active');
            } else {

                if(this.activeSeries) {
                    // deactivate the existing active series
                    this.deactivateSeries(this.activeSeries);
                }
        
                // activate the new one
                this.activeSeries = series;
                var series = this.chart.get(seriesId);
                series.options.marker = {
                    enabled: false,
                    symbol: 'circle',
                    radius: 4,
                    lineWidth: 2,
                    lineColor: 'transparent',
                    fillColor: 'transparent',
                    states: {
                        hover: {
                            enabled: true,
                            lineColor: 'rgba(50,143,176,1)',
                            lineWidth: 2,
                            symbol: 'circle',
                            radius: 6,
                        },
                    }
                }
                series.options.shadow = { color: '#24abcc', offsetX: 0, offsetY: 0, opacity: .3, width: 3 };                        
                series.options.color = activeColors[0];
                // series.options.lineWidth = 6;
                series.update(series.options);
                $target.addClass('active').siblings().removeClass('active');                    
            }
        },

        showSecondaryStatsPane: function(e) {
            var self = this;
            var $target = $(e.currentTarget);
            this.contentId = $target.data('id');
            this.onStatsSectionChange(e);
        },

        slideInSecondaryPane: function() {
            this.$('.secStatsContainer').velocity('stop', true).velocity('transition.expandIn', 140).addClass('active');
            this.scrollToTop();
        },

        secondaryPaneBeGone: function(e) {
            this.$('.secStatsContainer').velocity('stop', true).velocity('transition.expandOut', 140).html('').removeClass('active');
            this.onStatsSectionChange(e);
        },

        centerOfScreen: function() {
            var width = window.innerWidth ? window.innerWidth : document.documentElement.clientWidth ? document.documentElement.clientWidth : screen.width;
            return width/2;
        },

        togglePaymentList: function() {
            $('.paymentsList').toggle();
        },

        loadStoryPaginator: function() {
            var $listViewEl, url;
            var self = this;
            $listViewEl = self.$('.readArticleList');
            url = self.url + '?type=topstories&sort=reads&timeperiod=' + this.timePeriod;
                       
            self.statsTopStoriesListView && self.statsTopStoriesListView.destroy();
            self.statsTopStoriesListView = new PagedListView({
                el: $listViewEl,
                firstPage: true,
                url: url,
                templateName: 'story-stats-teaser',
                name: 'stats-topstories'
            });
            self.listenToOnce(self.statsTopStoriesListView, 'listViewReady', function() {
                self.statsTopStoriesListView.fetch();
            });
            self.listenToOnce(self.statsTopStoriesListView, 'noListViewResults', function() {
                self.$('.readArticleList .paginatedList').html('<div class="no-notifs noNotifs">No top stories to report yet...');
            });
        },

        showMoreAccrualData: function(e) {
            var self = this;
            var $ctarget = $(e.currentTarget);
            var isToday = $ctarget.data('today') || false;
            if(isToday) {

            }
            $ctarget.toggleClass('open');
            this.$('.accrualEgg').not($ctarget).removeClass('open');
        },

        clearData: function() {
            this.chartData.clear();
            var chart = this.chart;
            var seriesLength = chart.series.length;
            for(var i = seriesLength -1; i > -1; i--) {
                chart.series[i].remove();
            }
        },

        updateRange: function(e) {
            var self = this;
            var $target = $(e.currentTarget);
            $('.myStatsRangeSelector').text($target.text());
            $('.myStatsRange .dateChange li').removeClass('active');
            $target.parent('li').addClass('active');

            this.timePeriod = $target.data('time-period');

            this.$('.rangeItem').not($target).removeClass('selected');
            $target.addClass('selected');
            var $selectedHtml = $target.find('.innerBut').html();
            this.$('.activeRange .innerBut').html($selectedHtml);
            this.$('.topStoriesSubhead .range').html($selectedHtml);

            this.chart.showLoading();
            self.clearData();  
            this.fetchFreshData().then(function(data) {
                self.chart.hideLoading();
                self.chartData.set(data.chartdata);
                
                self.renderStatsSummary(data.summary);
                self.loadStoryPaginator();
            });
        },

        renderStatsSummary: function(data) {
            data = data || { placeholder: true };
            var self = this;
            var $html;
            var currentTarget = this.currentTarget;
            this.statsSummaryTmpl.done(function(tmpl) {
                $html = $(tmpl(data));
                self.$('.statsSummary').html($html);
            });
        },

        onStatsSectionChange: function(e) {
            var self = this;
            var $target = $(e.currentTarget);
            this.currentTarget = $target.data('target').replace('#', '');

            this.$('.seriesItem').not($target).removeClass('selected');
            $target.addClass('selected');
            var $selectedHtml = $target.find('.innerBut').html();
            this.$('.seriesSelector .innerBut').html($selectedHtml);
            self.chart.showLoading();
            self.clearData();  
            console.log('should be fetching and processing data');          
            this.fetchFreshData().then(function(data) {
                console.log(data);

                self.chartData.set(data.chartdata);
                self.chart.hideLoading();
                self.renderStatsSummary(data.summary);

                switch(self.currentTarget) {
                    case 'sec-story':
                        self.slideInSecondaryPane();
                        var contentContext = data.contentObj || '';
                        self.contentStatsTmpl.done(function(tmpl) {
                            var $statsContentPane = tmpl(contentContext);
                            self.$('.secStatsContainer').html($statsContentPane);
                        });
                    break;
                    default:                    
                        self.loadStoryPaginator();  
                    break;                  
                }
            });
        },

        updateChartSeries: function(target) {
            var self = this;
            var yAxis;
            var chartSeries = ['pageviews', 'repeats', 'retention', 'responses', 'words-added', 'words-removed', 'newposts'];
            this.chart.hideLoading();

            if(chartSeries && chartSeries.length) {
                for(var i=0, l=chartSeries.length, item ; i<l ; ++i) {
                    self.chart.addSeries(getSeries(self.chartData.get(chartSeries[i]), getSeriesOptions(chartSeries[i])));
                }
            }
        },

        resetZoom: function() {
            this.chart.zoomOut();
            this.$('.resetZoom').hide();
        },

        setZoom: function() {
            this.$('.resetZoom').show();
        },

        processArticleData: function(articles) {
            var processedArticles = {},
                //articlesPerDayChartData = [],
                utcDate = '',
                value = '';
            if(!articles) {
                return null;
            }
            for(var key in articles) {
                utcDate = Date.parse(key + ' UTC');
                value = articles[key];
                processedArticles[utcDate] = value;
                //articlesPerDayChartData.push([utcDate, value]);
            }
            return processedArticles;
        },

        highchartIt: function() {
            var self = this;
            var series = [];
            var defaultSeries = ['pageviews', 'repeats', 'retention', 'responses', 'words-added', 'words-removed', 'newposts']
            
            for(var i=0, l=defaultSeries.length, item ; i<l ; ++i) {
                console.log('setting up ' + defaultSeries[i]);
                series.push(getSeries(this.chartData.get(defaultSeries[i]), getSeriesOptions(defaultSeries[i])));
            }

            this.chart = Highcharts.StockChart({
                credits: { enabled: false },
                events: {
                    load: function(event) {
                        //When is chart ready?
                    }
                },                       
                chart: {
                    zoomType: 'x',
                    resetZoomButton: {
                        theme: {
                            display: 'none'
                        }
                    },                    
                    renderTo: self.$('.userStatsPlot').get(0),
                    plotBorderColor: 'rgba(0,0,0,.3)',
                    backgroundColor: '#6cd1c0',
                    plotBackgroundColor: '#6cd1c0',
                    spacingLeft: 0,
                    spacingRight: 0,
                    spacingTop: 0,
                    spacingBottom: 0,
                    ignoreHiddenSeries: true
                },
                rangeSelector : {
                    enabled: false
                },
                scrollbar : {
                    enabled : false
                },
                navigator : {
                    enabled : false
                },
                navigation: {
                    buttonOptions: {
                        enabled: false
                    }
                },
                title: {
                    text: null
                },
                plotOptions: {
                    column: {
                        stacking: 'normal'
                    },
                    line: {
                        stats: {
                            hover: {
                                column: 'yellow'
                            }
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'transparent',
                    borderColor: '#ccc',
                    borderRadius: 0,
                    borderWidth: 0,
                    useHTML: true,
                    snap: false,
                    shadow: false,
                    zIndex: 1000,
                    followPointer:true,
                    style: { fontFamily: '\'proxima-nova\'' },
                    positioner: function (labelWidth, labelHeight, point) {
                        var tooltipX, tooltipY;
                        if (point.plotX + labelWidth > this.chart.plotWidth) {
                            tooltipX = point.plotX + this.chart.plotLeft - labelWidth - 1;
                        } else {
                            tooltipX = point.plotX + this.chart.plotLeft + 1;
                        }
                        tooltipY = this.chart.plotTop + 100;
                        return {
                            x: tooltipX,
                            y: tooltipY
                        };
                    },
                    formatter: function() {
                        var tooltip = '',
                            date,
                            repeats = 0,
                            retention = 0,
                            pviews = 0,
                            wordsAdded = 0,
                            wordsRemoved = 0,
                            responses = 0,
                            percentage;
                            var activeSeries = self.activeSeries;
                        _(this.points).each(function(point) {
                            date = moment(point.x).format('ddd, MMM Do, YYYY');
                            switch(point.series.options.id) {
                                case 'pageviews-series':
                                //customize output here
                                    pviews = point.y;
                                    tooltip += '<div class="tipBlock"><div class="statNumber">' + point.y + '</div><div class="statLegendLabel">Views</div></div>';
                                break;
                                case 'repeat-series':
                                    repeats = point.y;
                                    tooltip += '<div class="tipBlock"><div class="statNumber">' + repeats + '</div><div class="statLegendLabel">Repeat visits</div></div>';
                                break;   
                                case 'retention-series':
                                    retention = point.y;
                                    tooltip += '<div class="tipBlock"><div class="statNumber">' + retention + '</div><div class="statLegendLabel">Repeat visits</div></div>';
                                break;                                                                
                                case 'responses-series':
                                //customize output here
                                    responses = point.y;
                                    tooltip += '<div class="tipBlock"><div class="statNumber percentage">' + point.y + '</div><div class="statLegendLabel">Responses</div></div>';
                                    break;
                                case 'words-added-series':
                                    wordsAdded = point.y;
                                    tooltip += '<div class="tipBlock"><div class="statNumber">' + wordsAdded + '</div><div class="statLegendLabel">added</div></div>';
                                    break;
                                case 'words-removed-series':
                                //customize output here
                                    wordsRemoved = point.y;
                                    tooltip += '<div class="tipBlock"><div class="statNumber">' + Math.abs(wordsRemoved) + '</div><div class="statLegendLabel">removed</div></div>';
                                    break;                                    
                            }
                        });
                        if(pviews) {

                        }
                        tooltip = '<p class="date">' + date + '</p>' + tooltip;
                        return tooltip;
                    }
                },
                yAxis: [
                {
                    // ##### yAxis 0
                    allowDecimals: false,
                    labels: {
                        style: {color: '#999'},
                        enabled: false
                    },
                    title: {
                        text: null
                    },
                    gridLineWidth: 1,
                    gridLineColor: 'rgba(0,0,0,.06)',
                    minorGridLineWidth: 0,
                    min: 0.0
                },

                {
                    // ##### yAxis 1
                    opposite: true,
                    allowDecimals: true,
                    gridLineWidth: 0,
                    gridLineColor: 'rgba(0,0,0,.02)',
                    minorGridLineWidth: 0,
                    labels: {
                        style: {
                            color: '#333333',
                            fontWeight: 'bold'
                        },
                        enabled: false
                    },
                    title: {
                        text: null
                    },
                    min: 0.0
                },
                {
                    // ##### yAxis 2
                    opposite: true,
                    allowDecimals: false,
                    gridLineWidth: 0,
                    minorGridLineWidth: 4,
                                        gridLineColor: 'rgba(0,0,0,.02)',
                    min: 0.0,
                    labels: {
                        enabled: false
                    },
                    title:{
                        text: null
                    }
                },
                {
                    // ##### yAxis 2
                    opposite: true,
                    allowDecimals: false,
                    gridLineWidth: 0,
                    minorGridLineWidth: 0,
                    labels: {
                        enabled: false
                    },
                    title:{
                        text: null
                    }
                }],
                xAxis: {
                    events: {
                        afterSetExtremes: function(event){
                            if (this.getExtremes().dataMin < event.min)
                                self.setZoom();
                        }
                    },                    
                    type: 'datetime',
                    crosshair: {
                        width: 3,
                        color: 'rgba(0,0,0,.05)',
                        dashStyle: 'solid'
                    },                 
                    labels: {
                        rotation: 0,
                        useHTML: true,                
                        style: {
                            marginTop: '-16px',
                            top: '-16px',
                            paddingTop: '0px',
                            color: '#ccc',
                        }
                    },
                    allowDecimals: false,
                    minRange: 7 * 24 * 3600 * 1000,
                    minTickInterval: 1000*60*60*24*30,
                    lineColor: '#e3e4e4',
                    lineWidth: 1,
                    minorTickLength: 0,
                    tickLength: 0,
                    title: {
                        text: null
                    }
                },
                legend: {
                    enabled: false
                },
                series: series
            });
            // this.chart.yAxis[0].setExtremes(null,(self.chart.yAxis[0].max * 1.2)); // add some headroom to the y-axis based on the initial max value
        },

        scrollToTop: function() {
            $('body').velocity("scroll", { 
              duration: 200,
              offset: 0
            });
        },

        destroy: function() {
            this.chart.destroy();            
        }


    });

    var getSeriesOptions = function(series) {
        var seriesOptions;
        switch(series) {
            case 'pageviews':
                seriesOptions = {
                    zIndex: 3,
                    type: 'spline',
                    dashStyle: 'solid',
                    color: 'rgba(255,255,255,.2)',
                    marker: {
                        enabled: false
                    },
                    name: 'pageviews',
                    lineWidth: 2,
                    states: {
                        hover: {
                         enabled: false,
                        }
                    },
                    shadow: { color: 'transparent', offsetX: 0, offsetY: 0, opacity: 0, width: 0 },
                    id: 'pageviews-series',
                    zIndex: 1,
                    yAxis: 0   
                }
            break;
            case 'retention':
                seriesOptions = {
                    type: 'spline',
                    marker: {
                        enabled: true,
                        symbol: 'circle',
                        radius: 0,
                        lineWidth: 1,
                        lineColor: 'rgba(0,0,0,.6)',
                        fillColor: 'rgba(0,0,0,.5)',
                        states: {
                            hover: {
                                enabled: false,
                                lineColor: 'rgba(50,143,176,1)',
                                lineWidth: 3,
                                symbol: 'circle',
                                radius: 6,
                            },
                        }
                    },
                    name: 'retention',
                    lineWidth: 2,
                    states: {
                        hover: {
                            enabled: false
                        },
                        active: {
                            lineColor: '#3a8bba',
                            color: '#3a8bba',
                            enabled: true,
                            lineWidth: 4,
                        },
                    },
                    id: 'retention-series',
                    color: 'rgba(255,255,255,.2)',
                    fillColor: '#f4f4ed',
                    zIndex: 3,
                    yAxis: 0   
                }
            break; 
            case 'repeat':
                seriesOptions = {
                    type: 'spline',
                    marker: {
                        enabled: true,
                        symbol: 'circle',
                        radius: 0,
                        lineWidth: 1,
                        lineColor: 'rgba(0,0,0,.6)',
                        fillColor: 'rgba(0,0,0,.5)',
                        states: {
                            hover: {
                                enabled: false,
                                lineColor: 'rgba(50,143,176,1)',
                                lineWidth: 3,
                                symbol: 'circle',
                                radius: 6,
                            },
                        }
                    },
                    name: 'repeat',
                    lineWidth: 2,
                    states: {
                        hover: {
                            enabled: false
                        },
                        active: {
                            lineColor: '#3a8bba',
                            color: '#3a8bba',
                            enabled: true,
                            lineWidth: 4,
                        },
                    },
                    id: 'repeat-series',
                    color: 'rgba(255,255,255,.2)',
                    fillColor: '#f4f4ed',
                    zIndex: 3,
                    yAxis: 0   
                }
            break; 
            case 'responses':
                seriesOptions = {
                    zIndex: 3,
                    type: 'spline',
                    dashStyle: 'solid',
                    color: 'rgba(255,255,255,.2)',
                    marker: {
                        enabled: false
                    },
                    name: 'responses',
                    lineWidth: 2,
                    states: {
                        hover: {
                         enabled: false,
                        }
                    },
                    shadow: { color: 'transparent', offsetX: 0, offsetY: 0, opacity: 0, width: 0 },
                    id: 'responses-series',
                    zIndex: 1,
                    yAxis: 2   
                }
            break;
            case 'words-added':
                seriesOptions = {
                    zIndex: 3,
                    type: 'areaspline',
                    dashStyle: 'solid',
                    color: 'rgba(255,255,255,.3)',
                    marker: {
                        enabled: false
                    },
                    name: 'words-added',
                    lineWidth: 0,
                    states: {
                        hover: {
                         enabled: false,
                        }
                    },
                    shadow: { color: 'transparent', offsetX: 0, offsetY: 0, opacity: 0, width: 0 },
                    id: 'words-added-series',
                    zIndex: 1,
                    yAxis: 3   
                }
            break;
            case 'words-removed':
                seriesOptions = {
                    zIndex: 3,
                    type: 'areaspline',
                    dashStyle: 'solid',
                    color: 'rgba(0,0,0,.3)',
                    marker: {
                        enabled: false
                    },
                    name: 'words-removed',
                    lineWidth: 0,
                    states: {
                        hover: {
                         enabled: false,
                        }
                    },
                    shadow: { color: 'transparent', offsetX: 0, offsetY: 0, opacity: 0, width: 0 },
                    id: 'words-removed-series',
                    zIndex: 1,
                    yAxis: 3   
                }
            break;
            }
        return seriesOptions           
    };

    var getSeries = function(data, options) {
        return _.extend({
            data: data
        }, options);
    };

    return StatsView;
});