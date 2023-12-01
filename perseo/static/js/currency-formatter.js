/*
  Currency formatting
  This is a CSS class to execute a jQuery to formatting currency on a text element.
*/
$(".currency").each(function () {
  // Get the value of the element
  var value = parseFloat($(this).text());
  // If the value is not a number, set it to 0
  if (isNaN(value)) {
    value = 0;
  }
  // Change the value to a formatted string like 1,000.0000
  var formatted = value.toFixed(4).replace(/\d(?=(\d{3})+\.)/g, "$&,");
  // Fill with spaces after the dollar sign
  var output = "$" + formatted.padStart(16, " ");
  // Set the formatted value to the element
  $(this).text(output);
});
