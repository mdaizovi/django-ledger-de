(function ($) {
  $(function () {
    var $entity = $("#id_entity");
    if (!$entity.length) {
      return;
    }

    $entity.on("change", function () {
      var value = $(this).val();
      if (!value) {
        return;
      }
      var url = new URL(window.location.href);
      url.searchParams.set("entity", value);
      window.location.assign(url.toString());
    });
  });
})(django.jQuery);
