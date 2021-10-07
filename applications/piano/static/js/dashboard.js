$(document).ready(function(){
    
  var openedTickets = document.getElementById('openedTickets');
  var closedTickets = document.getElementById('closedTickets');
  var inputOpenedTicket, filter, table, tr, td, i, txtValue;
  table = document.getElementById("datatableEvents");
  tr = table.getElementsByTagName("tr");
  //@TODO: terminar filtrado
  // openedTickets.onclick = function() {
  //   filterTable("abierto");
  // };

  // closedTickets.onclick = function() {
  //   filterTable("cerrado");
  // };

  // openedTickets.onmouseover = function() {
  //   this.style.background = 'red !important';
  // };
  // openedTickets.onmouseout = function() {
  //     this.style.backgroundColor = '';
  // };
  function filterTable(value){
    if (table.classList.contains('clicked')){
      inputOpenedTicket = false;
      table.classList.remove('clicked');
      for (i = 0; i < tr.length; i++) {
        tr[i].style.display = "";
      }
    }
    else{
      inputOpenedTicket = value;
      filter = inputOpenedTicket.toUpperCase();
      table.classList.add('clicked');
      for (i = 0; i < tr.length; i++) {
        td = tr[i].getElementsByTagName("td")[2];
        if (td) {
          txtValue = td.textContent || td.innerText;
          if (txtValue.toUpperCase().indexOf(filter) > -1) {
            tr[i].style.display = "";
          } else {
            tr[i].style.display = "none";
          }
        }       
      }
    }
  }

});

