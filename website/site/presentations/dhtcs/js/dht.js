var connections = function(node_id, size, result) {
    var i = 0;
    // closest
    for(i=-2; i<4; i++){
        var target = node_id+i;
        if(target<0) {
            target = size + i;
        }
        if(target >= size) {
            target = target-size;
        }
        if(node_id !== target){
            result.push({data: {source: node_id+'', target: target+''}});
        }
    }
    var peers = [6, 9, 12, 14, 17, 20, 23, 28, 34, 42, 50, 63, 78, 89];
    for(var i=0; i<peers.length; i++) {
        var p = peers[i];
        var n = node_id + p;
        if(n>=size) {
            n = n-size;
        }
        result.push({data: {source: node_id+'', target: n+''}});
    }
}

var make_edges = function(size) {
    var i = 0;
    var result = [];
    for(i=0; i<size; i++){
        connections(i, size, result);
    }
    return result;
}

$('#dhtNodes').cytoscape({
  style: cytoscape.stylesheet()
    .selector('node')
      .css({
        'content': 'data(name)',
        'text-valign': 'center',
        'color': 'white',
        'text-outline-width': 2,
        'text-outline-color': '#888',
        'font-size': '8px'
      })
    .selector('edge')
      .css({
        'target-arrow-shape': 'triangle'
      })
    .selector(':selected')
      .css({
        'background-color': 'black',
        'line-color': 'black',
        'target-arrow-color': 'black',
        'source-arrow-color': 'black'
      })
    .selector('.faded')
      .css({
        'opacity': 0.05,
        'text-opacity': 0.2
      }),
  elements: {
    nodes: function(amount) {
      result = [];
      for(var i=0; i<amount; i++) {
        result.push({data: {id: i+'', name: 'node: '+i+''}});
      }
      return result;
    }(100),
    edges: make_edges(100)
  },

  ready: function(){
    window.cy = this;

    // giddy up...

    cy.elements().unselectify();

    cy.on('tap', 'node', function(e){
      var node = e.cyTarget;
      var neighborhood = node.neighborhood().add(node);

      cy.elements().addClass('faded');
      neighborhood.removeClass('faded');
    });

    cy.on('tap', function(e){
      if( e.cyTarget === cy ){
        cy.elements().removeClass('faded');
      }
    });
  }
});
