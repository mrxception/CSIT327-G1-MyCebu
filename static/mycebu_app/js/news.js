document.addEventListener("DOMContentLoaded", function () {
  var newsItems = [
    {
      id: "1",
      title: "New Online Services Portal Launched",
      description: "Cebu City launches enhanced digital services platform for faster permit processing",
      content: "The Cebu City Government has officially launched its new online services portal, making it easier for citizens to access government services from the comfort of their homes.",
      category: "Government Services",
      tags: ["Digital Transformation", "Public Services", "Technology"],
      date: "2025-01-15"
    },
    {
      id: "2",
      title: "Infrastructure Development Update",
      description: "Major road improvements scheduled for Q1 2025",
      content: "Several key roads in both North and South districts will undergo maintenance and improvements to enhance traffic flow and safety.",
      category: "Infrastructure",
      tags: ["Roads", "Development", "Traffic"],
      date: "2025-01-12"
    },
    {
      id: "3",
      title: "Community Health Programs Expanded",
      description: "Free health check-ups available at all barangay health centers",
      content: "The City Health Office announces expansion of free health services including consultations, basic laboratory tests, and preventive care programs.",
      category: "Health",
      tags: ["Healthcare", "Community", "Wellness"],
      date: "2025-01-10"
    },
    {
      id: "4",
      title: "Business Permit Processing Accelerated",
      description: "New streamlined process reduces permit approval time by 50%",
      content: "The BPLO introduces new measures to expedite business permit processing, supporting local entrepreneurs and business growth.",
      category: "Business",
      tags: ["Business", "Permits", "Economy"],
      date: "2025-01-08"
    },
    {
      id: "5",
      title: "Environmental Initiative Launched",
      description: "City-wide tree planting and coastal cleanup programs announced",
      content: "Join the Cebu City Government in our commitment to environmental sustainability through various green initiatives throughout the year.",
      category: "Environment",
      tags: ["Environment", "Sustainability", "Community"],
      date: "2025-01-05"
    },
    {
      id: "6",
      title: "Public Safety Advisory",
      description: "Enhanced security measures during holiday season",
      content: "The Cebu City Police Office announces increased patrols and security checkpoints to ensure public safety during the festive season.",
      category: "Public Safety",
      tags: ["Safety", "Security", "Emergency"],
      date: "2025-01-03"
    }
  ];

  var categories = ["All"].concat(
    Array.from(new Set(newsItems.map(function (n) { return n.category; })))
  );

  var allTags = Array.from(
    new Set(newsItems.flatMap(function (n) { return n.tags; }))
  );

  var selectedCategory = "All";
  var selectedTag = null;

  var categoryContainer = document.getElementById("news-category-tabs");
  var tagsContainer = document.getElementById("news-tags");
  var grid = document.getElementById("news-grid");
  var empty = document.getElementById("news-empty");

  function formatDate(value) {
    var d = new Date(value + "T00:00:00");
    if (isNaN(d.getTime())) return value;
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric"
    });
  }

  function updateUnderline() {
    if (!categoryContainer) return;
    var active = categoryContainer.querySelector(".tab-btn.is-active");
    if (!active) {
      categoryContainer.style.setProperty("--tab-x", "8px");
      categoryContainer.style.setProperty("--tab-w", "0px");
      return;
    }
    var rect = active.getBoundingClientRect();
    var parentRect = categoryContainer.getBoundingClientRect();
    var x = rect.left - parentRect.left + categoryContainer.scrollLeft;
    categoryContainer.style.setProperty("--tab-x", x + "px");
    categoryContainer.style.setProperty("--tab-w", rect.width + "px");
  }

  function renderCategories() {
    if (!categoryContainer) return;
    categoryContainer.innerHTML = "";
    categories.forEach(function (cat) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "tab-btn" + (cat === selectedCategory ? " is-active" : "");
      btn.textContent = cat;
      btn.dataset.category = cat;
      btn.addEventListener("click", function () {
        selectedCategory = cat;
        var buttons = categoryContainer.querySelectorAll(".tab-btn");
        buttons.forEach(function (b) { b.classList.remove("is-active"); });
        btn.classList.add("is-active");
        applyFilters();
        updateUnderline();
      });
      categoryContainer.appendChild(btn);
    });
    updateUnderline();
  }

  function renderTags() {
    if (!tagsContainer) return;
    tagsContainer.innerHTML = "";

    var allButton = document.createElement("button");
    allButton.type = "button";
    allButton.className = "news-tag" + (selectedTag === null ? " is-active" : "");

    var allIcon = document.createElement("span");
    allIcon.className = "material-icons news-tag-icon";
    allIcon.textContent = "sell";

    var allLabel = document.createElement("span");
    allLabel.textContent = "All Tags";

    allButton.appendChild(allIcon);
    allButton.appendChild(allLabel);

    allButton.addEventListener("click", function () {
      selectedTag = null;
      var buttons = tagsContainer.querySelectorAll(".news-tag");
      buttons.forEach(function (b) { b.classList.remove("is-active"); });
      allButton.classList.add("is-active");
      applyFilters();
    });

    tagsContainer.appendChild(allButton);

    allTags.forEach(function (tag) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "news-tag" + (selectedTag === tag ? " is-active" : "");

      var icon = document.createElement("span");
      icon.className = "material-icons news-tag-icon";
      icon.textContent = "sell";

      var label = document.createElement("span");
      label.textContent = tag;

      btn.appendChild(icon);
      btn.appendChild(label);

      btn.addEventListener("click", function () {
        if (selectedTag === tag) {
          selectedTag = null;
        } else {
          selectedTag = tag;
        }
        var buttons = tagsContainer.querySelectorAll(".news-tag");
        buttons.forEach(function (b) { b.classList.remove("is-active"); });
        if (selectedTag === null) {
          allButton.classList.add("is-active");
        } else {
          btn.classList.add("is-active");
        }
        applyFilters();
      });

      tagsContainer.appendChild(btn);
    });
  }

  function renderNews(list) {
    if (!grid || !empty) return;
    grid.innerHTML = "";
    if (!list.length) {
      empty.style.display = "block";
      return;
    }
    empty.style.display = "none";

    list.forEach(function (item) {
      var card = document.createElement("article");
      card.className = "news-card";

      var head = document.createElement("div");
      head.className = "news-card__head";

      var categoryBadge = document.createElement("div");
      categoryBadge.className = "news-badge";
      categoryBadge.textContent = item.category;

      var dateBox = document.createElement("div");
      dateBox.className = "news-date";

      var dateIcon = document.createElement("span");
      dateIcon.className = "news-date-icon";
      dateIcon.innerHTML =
        '<svg viewBox="0 0 24 24" aria-hidden="true">' +
        '<path d="M7 2v2M17 2v2M4 9h16M5 5h14a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1z" ' +
        'fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>' +
        "</svg>";

      var dateText = document.createElement("span");
      dateText.textContent = formatDate(item.date);

      dateBox.appendChild(dateIcon);
      dateBox.appendChild(dateText);

      head.appendChild(categoryBadge);
      head.appendChild(dateBox);

      var title = document.createElement("h3");
      title.className = "news-card__title";
      title.textContent = item.title;

      var desc = document.createElement("p");
      desc.className = "news-card__desc";
      desc.textContent = item.description;

      var body = document.createElement("p");
      body.className = "news-card__body";
      body.textContent = item.content;

      var tagsRow = document.createElement("div");
      tagsRow.className = "news-card__tags";

      item.tags.forEach(function (tag) {
        var chip = document.createElement("button");
        chip.type = "button";
        chip.className = "news-chip";
        chip.textContent = tag;
        chip.addEventListener("click", function () {
          selectedTag = tag;
          renderTags();
          applyFilters();
        });
        tagsRow.appendChild(chip);
      });

      card.appendChild(head);
      card.appendChild(title);
      card.appendChild(desc);
      card.appendChild(body);
      card.appendChild(tagsRow);

      grid.appendChild(card);
    });
  }

  function applyFilters() {
    var filtered = newsItems.filter(function (item) {
      var categoryMatch =
        selectedCategory === "All" || item.category === selectedCategory;
      var tagMatch =
        selectedTag === null || item.tags.indexOf(selectedTag) !== -1;
      return categoryMatch && tagMatch;
    });
    renderNews(filtered);
  }

  renderCategories();
  renderTags();
  applyFilters();

  window.addEventListener("resize", function () {
    updateUnderline();
  });
});
