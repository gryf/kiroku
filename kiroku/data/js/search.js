/*
 * Simple search functionality.
 * Part of the Kiroku project.
 */
(function () {
    "use strict";
    var data,
        templates;

    if (!String.prototype.swap) {
        String.prototype.swap = function (obj) {
            return this.replace(
                /\{([^{}]*)\}/g,
                function (originalStr, subStr) {
                    var result = obj[subStr];
                    return typeof result === 'string' ||
                        typeof result === 'number' ? result : originalStr;
                }
            );
        };
    }

    function notFound(searchString) {
        $("article").html(templates.n.swap({'sp': searchString}));
    }

    function parseItems(searchString) {
        var res = {},
            artIds = [],
            weights = {},
            weights2 = {},
            weights3 = [],
            html = [],
            words = [],
            notFoundFlag = false;

        searchString.split(" ").forEach(function (item) {
            if (item) {
                words.push(item);
            }
        });

        words.forEach(function (item) {
            if (!data.w[item]) {
                notFoundFlag = true;
            } else {
                res[item] = data.w[item];
            }
        });

        if (notFoundFlag) {
            notFound(searchString);
            return false;
        }

        $.each(res, function (item, value) {
            var tempIds = [];
            if (!artIds.length) {
                value.forEach(function (artWeight) {
                    artIds.push(artWeight[0]);
                    weights[artWeight[0]] = artWeight[1];
                });
            } else {
                value.forEach(function (artWeight) {
                    if (artIds.indexOf(artWeight[0]) > -1) {
                        tempIds.push(artWeight[0]);
                        weights[artWeight[0]] += artWeight[1];
                    } else {
                        delete weights[artWeight[0]];
                    }
                });
                artIds = tempIds;
            }
        });

        artIds.forEach(function (artId) {
            if (!(weights[artId] in weights2)) {
                weights2[weights[artId]] = [];
            }
            weights2[weights[artId]].push(artId);
            weights3.push(weights[artId]);
        });

        weights3.sort();
        weights3 = $.unique(weights3);
        weights3.sort(function (first, second) {
            return second - first;
        });

        weights3.forEach(function (weight) {
            weights2[weight].forEach(function (idx) {
                html.push(data.a[idx]);
            });
        });

        if (html.length === 0) {
            notFound(searchString);
        } else {
            $("article").html(templates.r.swap({'sp': searchString}) +
                              html.join(" "));
        }
        return false;
    }

    $(function () {
        if (!templates) {
            $.getJSON("templates.json", {async: false})
            .done(function (res) {
                templates = res;
            });
        }

        $("#searchform input").keypress(function (event) {
            var searchString;
            if (event.which === 13) {
                $("article").html(templates.w);
                searchString = this.value;
                event.preventDefault();
                $(document).attr('title', templates.t);

                if (!data) {
                    $.getJSON("search.json", {async: false})
                    .done(function (res) {
                        data = res;
                        parseItems(searchString);
                    });
                } else {
                    parseItems(searchString);
                }
            }
        });
    });
})();
