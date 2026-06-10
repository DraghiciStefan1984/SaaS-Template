# Create a New SaaS From This Template

1. Create a new repository from this template.
2. Rename project metadata, package names, frontend title, and environment variables.
3. Keep the common UI shell and design tokens.
4. Add product-specific backend code under `backend/apps/products/<product_name>/`.
   Start with `npm run product:scaffold -- --slug product-slug --name "Product Name"`.
5. Add provider clients behind the integrations service layer.
6. Add AI task profiles/model policies before adding provider-specific AI calls.
7. Add AI workflows behind the AI service layer.
8. Extend the structured report content through the report model/generator pattern;
   reuse generic JSON, CSV, HTML, PDF, and DOCX download rendering.
9. Configure Stripe price IDs, feature flags, and usage limits.
10. Add product-specific frontend pages using shared components.
11. Run tests, security checks, and deployment checklist before launch.
12. Regenerate frontend API route types with `npm run api:types` after contract changes.
13. Use the in-app notification service for user-visible workflow state and keep
    sensitive delivery/provider details in admin-only delivery logs.
