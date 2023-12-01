/*
  Currency formatting
  This is a CSS class to execute a jQuery to formatting currency on a text element.
*/
$(".currency").each(function () {
  var value = parseFloat($(this).text());
  // Change the value to a formatted string like 1,000.0000
  var formatted = value.toFixed(4).replace(/\d(?=(\d{3})+\.)/g, "$&,");
  // var formatted = value.toLocaleString("es-ES", {
  //   style: "currency",
  //   currency: "USD",
  // });
  // Fill whit spaces after the dollar sign
  var output = "$" + formatted.padStart(16, " ");
  // Set the formatted value to the element
  console.log(output);
  $(this).text(output);
});
