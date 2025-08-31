# Inventory Pro - Modern Corporate Design System
## Style Guide & Component Library

### 🎨 **Color Palette**

#### Primary Colors
- **Primary Blue**: `#1e40af` (bg-blue-700), `#3b82f6` (bg-blue-600)
- **Primary Light**: `#dbeafe` (bg-blue-100), `#bfdbfe` (bg-blue-200)

#### Status Colors
- **Success Green**: `#059669` (bg-emerald-600), `#10b981` (bg-emerald-500)
- **Success Light**: `#dcfdf7` (bg-emerald-100), `#a7f3d0` (bg-emerald-200)

- **Warning Yellow**: `#d97706` (bg-amber-600), `#f59e0b` (bg-amber-500)
- **Warning Light**: `#fef3c7` (bg-amber-100), `#fde68a` (bg-amber-200)

- **Danger Red**: `#dc2626` (bg-red-600), `#ef4444` (bg-red-500)
- **Danger Light**: `#fee2e2` (bg-red-100), `#fecaca` (bg-red-200)

#### Neutral Colors
- **Background**: `#f9fafb` (bg-gray-50)
- **Surface**: `#ffffff` (bg-white)
- **Border**: `#e5e7eb` (border-gray-200), `#d1d5db` (border-gray-300)
- **Text Primary**: `#111827` (text-gray-900)
- **Text Secondary**: `#6b7280` (text-gray-500)

---

### 🧩 **Component System**

#### Navigation Components
```css
.nav-item {
  @apply px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded-lg transition-all duration-200 no-underline;
}
.nav-item-active {
  @apply text-blue-600 bg-blue-50 hover:text-blue-700 hover:bg-blue-100;
}
```

#### Card System
```css
.card {
  @apply bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden;
}
.card-header {
  @apply px-6 py-4 border-b border-gray-200 bg-gray-50;
}
.card-body {
  @apply p-6;
}
.card-compact {
  @apply p-4;
}
```

#### Button System
```css
.btn-primary {
  @apply inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-all duration-200 no-underline;
}
.btn-secondary {
  @apply inline-flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-all duration-200 no-underline;
}
.btn-success {
  @apply inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-lg hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500 focus:ring-offset-2 transition-all duration-200 no-underline;
}
.btn-danger {
  @apply inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-red-600 border border-transparent rounded-lg hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 transition-all duration-200 no-underline;
}
.btn-sm { @apply px-3 py-1.5 text-xs; }
.btn-lg { @apply px-6 py-3 text-base; }
.btn-square { @apply inline-flex items-center justify-center w-8 h-8 p-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-all duration-200; }
```

#### Form Controls
```css
.form-input {
  @apply block w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200;
}
.form-select {
  @apply block w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200;
}
.form-label {
  @apply block text-sm font-medium text-gray-700 mb-1;
}
.form-error {
  @apply text-sm text-red-600 mt-1;
}
```

#### Status Badges
```css
.badge {
  @apply inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium;
}
.badge-success { @apply bg-green-100 text-green-800; }
.badge-warning { @apply bg-yellow-100 text-yellow-800; }
.badge-error { @apply bg-red-100 text-red-800; }
.badge-info { @apply bg-blue-100 text-blue-800; }
.badge-gray { @apply bg-gray-100 text-gray-800; }
```

#### Page Layout
```css
.page-header {
  @apply bg-white border-b border-gray-200 px-6 py-4;
}
.page-title {
  @apply text-2xl font-bold text-gray-900;
}
.page-subtitle {
  @apply text-sm text-gray-600 mt-1;
}
.page-content {
  @apply flex-1 p-6 bg-gray-50;
}
```

---

### 📐 **Layout Patterns**

#### Top Navigation Structure
```html
<nav class="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-40">
  <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
    <div class="flex justify-between h-16">
      <!-- Logo & Main Nav -->
      <!-- User Menu & Actions -->
    </div>
  </div>
</nav>
```

#### Page Header Pattern
```html
<div class="page-header">
  <div class="flex items-center justify-between">
    <div>
      <h1 class="page-title">Page Title</h1>
      <p class="page-subtitle">Descriptive subtitle</p>
    </div>
    <div class="flex items-center space-x-3">
      <!-- Action buttons -->
    </div>
  </div>
</div>
```

#### Stats Cards Pattern
```html
<div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
  <div class="card">
    <div class="card-compact">
      <div class="flex items-center">
        <div class="flex-shrink-0">
          <div class="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
            <!-- Icon -->
          </div>
        </div>
        <div class="ml-4">
          <p class="text-sm font-medium text-gray-500">Label</p>
          <p class="text-2xl font-semibold text-gray-900">Value</p>
        </div>
      </div>
    </div>
  </div>
</div>
```

#### Search & Filter Pattern
```html
<div class="card mb-6">
  <div class="card-body">
    <form method="get" class="grid grid-cols-1 lg:grid-cols-4 gap-4">
      <!-- Form controls -->
    </form>
  </div>
</div>
```

---

### 🎯 **Implementation Guidelines**

#### DO's
- ✅ Use consistent spacing (4px, 8px, 16px, 24px, 32px)
- ✅ Apply hover states to interactive elements
- ✅ Use proper semantic HTML
- ✅ Include loading and error states
- ✅ Make components accessible (ARIA labels, focus states)
- ✅ Use consistent border radius (8px for most elements, 12px for large cards)

#### DON'Ts
- ❌ Mix different button styles on the same page
- ❌ Use inconsistent color variations
- ❌ Create custom components without following the system
- ❌ Skip focus and hover states
- ❌ Use inline styles instead of component classes

---

### 🔧 **Functional Requirements Preserved**

#### Items Page Functionality
- ✅ Inline editing with expandable rows
- ✅ Bulk selection and actions
- ✅ Search and filtering
- ✅ CSV upload functionality
- ✅ Pagination
- ✅ Stock status indicators
- ✅ Real-time updates

#### All Pages Must Include
- ✅ Consistent top navigation
- ✅ Page headers with titles and action buttons
- ✅ Search functionality where applicable
- ✅ Proper form validation and error handling
- ✅ Loading states for async operations
- ✅ Responsive design
- ✅ Accessibility features

---

### 📱 **Responsive Design**

#### Breakpoints
- **Mobile**: `max-md:` (up to 768px)
- **Tablet**: `md:` (768px and up)
- **Desktop**: `lg:` (1024px and up)
- **Large Desktop**: `xl:` (1280px and up)

#### Responsive Patterns
```html
<!-- Grid that stacks on mobile -->
<div class="grid grid-cols-1 md:grid-cols-4 gap-6">

<!-- Hide on mobile -->
<div class="hidden md:block">

<!-- Full width on mobile -->
<div class="w-full md:w-auto">
```

---

### 🚀 **Next Steps**

1. **Apply to All Pages**: Update all templates with consistent design system
2. **Create Component Documentation**: Document all reusable components
3. **Test Functionality**: Ensure all existing features continue to work
4. **Performance Optimization**: Minimize CSS and optimize for speed
5. **Accessibility Audit**: Ensure WCAG compliance across all pages

This design system ensures consistency, professionalism, and maintainability across your entire inventory application while preserving all existing functionality.
