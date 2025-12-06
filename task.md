# Task List - Missing Features Implementation Plan

## 📋 Overview

This document outlines the implementation plan for missing features to align the Fresh Product Replenishment Manager with the original vision. The plan is organized by priority and includes technical specifications, dependencies, and acceptance criteria.

**Last Updated:** 2024-01-XX  
**Status:** Planning Phase

---

## 🎯 Priority Levels

- **P0 - Critical:** Must have for core functionality (blocks MVP completion)
- **P1 - High:** Important for user experience (should have)
- **P2 - Medium:** Nice to have, improves usability
- **P3 - Low:** Future enhancements

---

## 📊 Implementation Status

| Priority | Total Tasks | Not Started | In Progress | Completed |
|----------|-------------|-------------|-------------|-----------|
| P0 | 6 | 6 | 0 | 0 |
| P1 | 8 | 8 | 0 | 0 |
| P2 | 4 | 4 | 0 | 0 |
| P3 | 3 | 3 | 0 | 0 |
| **Total** | **21** | **21** | **0** | **0** |

---

## 🔴 P0 - Critical Features

### Task 1: Shelf vs Stock Inventory Separation

**Status:** Not Started  
**Estimated Effort:** 8 hours  
**Dependencies:** None

#### Description
Implement clear distinction between products on shelves (display) and products in stock (backroom/warehouse). This is fundamental to the manager's daily operations.

#### Technical Requirements

**Backend Changes:**
1. **Database Schema Updates:**
   - Add `shelf_quantity` column to `InventorySnapshot` table
   - Add `backroom_quantity` column to `InventorySnapshot` table
   - Create migration script: `scripts/migrations/add_shelf_stock_separation.py`
   - Update `services/api_gateway/models.py`:
     ```python
     class InventorySnapshot(Base):
         # ... existing fields ...
         shelf_quantity = Column(Float, nullable=False, default=0.0)
         backroom_quantity = Column(Float, nullable=False, default=0.0)
         # quantity = shelf_quantity + backroom_quantity (computed property)
     ```

2. **API Updates:**
   - Update `InventoryItemResponse` schema in `services/api_gateway/schemas.py`:
     ```python
     class InventoryItemResponse(BaseModel):
         # ... existing fields ...
         shelf_quantity: float
         backroom_quantity: float
         total_quantity: float  # computed
     ```
   - Update `get_store_inventory` endpoint in `services/api_gateway/store_routes.py` to return shelf/backroom quantities
   - Add validation: `shelf_quantity + backroom_quantity = total_quantity`

3. **Service Layer:**
   - Update `services/api_gateway/store_routes.py` to calculate shelf/backroom from inventory snapshots
   - Add helper function to split inventory if not already separated

**Frontend Changes:**
1. **Inventory Page Updates:**
   - Update `apps/store-manager-frontend/src/pages/InventoryPage.tsx`:
     - Add columns: "On Shelves", "In Stock (Backroom)", "Total"
     - Add visual indicators (icons) for shelf vs stock
     - Add summary cards showing shelf vs stock totals

2. **Dashboard Updates:**
   - Update `apps/store-manager-frontend/src/pages/DashboardPage.tsx`:
     - Replace "On Shelves" metric with breakdown: "X on shelves, Y in stock"
     - Add separate KPI cards for shelf and stock quantities

3. **Interface Updates:**
   - Update `InventoryItem` interface in `InventoryPage.tsx`:
     ```typescript
     interface InventoryItem {
       // ... existing fields ...
       shelf_quantity: number
       backroom_quantity: number
       total_quantity: number
     }
     ```

#### Acceptance Criteria
- [ ] Database schema includes `shelf_quantity` and `backroom_quantity` columns
- [ ] API returns shelf and backroom quantities separately
- [ ] Frontend displays shelf vs stock clearly
- [ ] Dashboard shows breakdown of shelf vs stock
- [ ] Migration script successfully updates existing data
- [ ] Unit tests pass for new inventory separation logic

#### Testing Requirements
- Unit tests for inventory separation calculations
- Integration tests for API endpoints
- Frontend component tests for inventory display
- Migration script tests with sample data

---

### Task 2: Refill Dashboard Page

**Status:** Not Started  
**Estimated Effort:** 12 hours  
**Dependencies:** Task 1 (Shelf vs Stock), Task 3 (Transit Time Integration)

#### Description
Create a dedicated "Refill Dashboard" that shows managers exactly how much to refill shelves for tomorrow, considering all factors (forecast, current stock, transit time, expiry).

#### Technical Requirements

**Backend Changes:**
1. **New API Endpoint:**
   - Create `GET /api/v1/stores/{store_id}/refill-plan` in `services/api_gateway/store_routes.py`
   - Response schema:
     ```python
     class RefillItemResponse(BaseModel):
         sku_id: str
         product_name: str
         current_shelf_quantity: float
         current_backroom_quantity: float
         forecasted_demand_tomorrow: float
         recommended_shelf_quantity: float
         refill_quantity: float  # How much to move from backroom to shelf
         order_quantity: float  # How much to order (if needed)
         in_transit_quantity: float
         expected_arrival_date: Optional[str]
         transit_days: int
         factors: Dict[str, Any]  # weather, day_of_week, holiday, etc.
     ```

2. **Service Logic:**
   - Create `services/api_gateway/refill_service.py`:
     ```python
     class RefillService:
         def calculate_refill_plan(
             self,
             store_id: str,
             target_date: date,
             current_inventory: List[Dict]
         ) -> List[RefillItemResponse]:
             # 1. Get forecast for tomorrow
             # 2. Get current shelf/stock quantities
             # 3. Get in-transit orders with arrival dates
             # 4. Calculate recommended shelf quantity (based on forecast)
             # 5. Calculate refill quantity (recommended - current shelf)
             # 6. Factor in transit time and expected arrivals
             # 7. Return refill plan
     ```

3. **Refill Calculation Logic:**
   - Recommended shelf quantity = forecasted_demand_tomorrow * safety_factor
   - Refill quantity = max(0, recommended_shelf_quantity - current_shelf_quantity)
   - If refill > backroom_quantity: trigger order recommendation
   - Consider in-transit items arriving before target date

**Frontend Changes:**
1. **New Page:**
   - Create `apps/store-manager-frontend/src/pages/RefillPage.tsx`
   - Layout:
     - Header: "Tomorrow's Refill Plan - [Date]"
     - Summary cards: Total items to refill, Total to order, Items in transit
     - Table: Detailed refill plan per product
     - Action buttons: "Approve All", "Export to CSV"

2. **Refill Table Columns:**
   - Product Name
   - Current (Shelf / Stock)
   - Forecast Tomorrow
   - Recommended Shelf Qty
   - Refill Qty (highlighted)
   - Order Qty (if needed)
   - In Transit (with arrival date)
   - Factors (weather, day, holiday icons)

3. **Visual Indicators:**
   - Color coding: Green (sufficient stock), Yellow (needs refill), Red (needs order)
   - Icons for factors: 🌤️ Weather, 📅 Day of week, 🎉 Holiday
   - Progress bars showing shelf fill percentage

4. **API Integration:**
   - Add `getRefillPlan(storeId, targetDate)` to `apps/store-manager-frontend/src/services/api.ts`
   - Use React Query for data fetching
   - Auto-refresh every 5 minutes

#### Acceptance Criteria
- [ ] New refill dashboard page exists and is accessible
- [ ] Shows clear "how much to refill shelves for tomorrow"
- [ ] Displays all factors (weather, day, holiday) affecting forecast
- [ ] Considers transit time and expected arrivals
- [ ] Shows both refill quantities and order quantities
- [ ] Export to CSV functionality works
- [ ] Visual indicators are clear and intuitive
- [ ] API endpoint returns accurate refill calculations

#### Testing Requirements
- Unit tests for refill calculation logic
- Integration tests for refill API endpoint
- Frontend component tests for refill dashboard
- E2E test: Complete refill workflow

---

### Task 3: Transit Time Integration

**Status:** Not Started  
**Estimated Effort:** 6 hours  
**Dependencies:** None

#### Description
Properly integrate transit time into refill and ordering calculations. Show expected arrival dates and factor them into inventory planning.

#### Technical Requirements

**Backend Changes:**
1. **Database Schema:**
   - Add `transit_days` column to `Product` table (default per product)
   - Add `expected_arrival_date` to order tracking (if not exists)
   - Create `Order` table if missing:
     ```python
     class Order(Base):
         id = Column(Integer, primary_key=True)
         store_id = Column(Integer, ForeignKey("stores.id"))
         product_id = Column(Integer, ForeignKey("products.id"))
         order_quantity = Column(Float)
         order_date = Column(Date)
         expected_arrival_date = Column(Date)
         actual_arrival_date = Column(Date, nullable=True)
         status = Column(String)  # pending, in_transit, delivered, cancelled
         transit_days = Column(Integer)
     ```

2. **Service Updates:**
   - Update `ReplenishmentService` to consider transit time:
     - Calculate expected arrival date = order_date + transit_days
     - Factor in-transit items arriving before target date
   - Update `services/api_gateway/services.py`:
     ```python
     def _get_in_transit_items(
         self,
         store_id: str,
         target_date: date
     ) -> List[Dict]:
         # Get orders with expected_arrival_date <= target_date
         # Return items that will arrive in time
     ```

3. **API Updates:**
   - Update inventory endpoints to show expected arrival dates
   - Add transit time to product responses

**Frontend Changes:**
1. **Inventory Page:**
   - Show expected arrival date for in-transit items
   - Add countdown: "Arrives in X days"
   - Color code: Green (arrives on time), Yellow (late), Red (overdue)

2. **Refill Dashboard:**
   - Show which in-transit items will arrive before tomorrow
   - Factor them into refill calculations
   - Display transit timeline

3. **Orders Page:**
   - Show expected arrival dates
   - Add transit status tracking
   - Allow updating actual arrival date

#### Acceptance Criteria
- [ ] Transit time is stored per product
- [ ] Expected arrival dates are calculated correctly
- [ ] In-transit items are factored into refill calculations
- [ ] Frontend displays expected arrival dates clearly
- [ ] Transit time affects order recommendations
- [ ] Late/overdue items are highlighted

#### Testing Requirements
- Unit tests for transit time calculations
- Integration tests for order tracking
- Frontend tests for arrival date display

---

### Task 4: Real-Time Notifications System

**Status:** Not Started  
**Estimated Effort:** 10 hours  
**Dependencies:** None

#### Description
Replace hardcoded alerts with a real-time notification system that alerts managers about critical events (empty shelves, low stock, expiring items, orders arriving).

#### Technical Requirements

**Backend Changes:**
1. **Database Schema:**
   - Create `Notification` table:
     ```python
     class Notification(Base):
         id = Column(Integer, primary_key=True)
         user_id = Column(Integer, ForeignKey("users.id"))
         store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
         type = Column(String)  # empty_shelf, low_stock, expiring, order_arrived, etc.
         severity = Column(String)  # info, warning, error, critical
         title = Column(String)
         message = Column(String)
         data = Column(JSON)  # Additional context
         read = Column(Boolean, default=False)
         created_at = Column(DateTime, default=datetime.utcnow)
     ```

2. **Notification Service:**
   - Create `services/api_gateway/notification_service.py`:
     ```python
     class NotificationService:
         def check_and_create_notifications(
             self,
             store_id: str,
             db: Session
         ) -> List[Notification]:
             # Check for:
             # - Empty shelves
             # - Low stock items
             # - Items expiring in 1-3 days
             # - Orders arriving today
             # - Stockout risks
         ```

3. **API Endpoints:**
   - `GET /api/v1/notifications` - Get user's notifications
   - `POST /api/v1/notifications/{id}/read` - Mark as read
   - `POST /api/v1/notifications/read-all` - Mark all as read
   - `GET /api/v1/stores/{store_id}/notifications` - Get store notifications

4. **Background Job:**
   - Create `scripts/generate_notifications.py`:
     - Run periodically (every 15 minutes)
     - Check all stores for alert conditions
     - Create notifications in database

**Frontend Changes:**
1. **Notification Provider:**
   - Update `apps/store-manager-frontend/src/components/notifications/NotificationProvider.tsx`:
     - Connect to real API instead of mock data
     - Poll for new notifications every 30 seconds
     - Show notification badge with count

2. **Alerts List:**
   - Update `apps/store-manager-frontend/src/components/dashboard/AlertsList.tsx`:
     - Fetch from `/api/v1/notifications` endpoint
     - Display real notifications
     - Add "Mark as read" functionality
     - Filter by severity

3. **Notification Center:**
   - Create `apps/store-manager-frontend/src/components/notifications/NotificationCenter.tsx`:
     - Dropdown/bell icon in header
     - List of all notifications
     - Group by type/severity
     - Mark as read/unread
     - Clear all functionality

4. **Real-Time Updates:**
   - Consider WebSocket integration for instant notifications (future)
   - For now: Polling every 30 seconds

#### Acceptance Criteria
- [ ] Notification table exists in database
- [ ] Notification service checks all alert conditions
- [ ] API endpoints return real notifications
- [ ] Frontend displays real notifications (not hardcoded)
- [ ] Notifications are created for: empty shelves, low stock, expiring items, orders
- [ ] Users can mark notifications as read
- [ ] Notification badge shows unread count
- [ ] Background job runs and creates notifications

#### Testing Requirements
- Unit tests for notification service logic
- Integration tests for notification API
- Frontend tests for notification display
- E2E test: Notification creation and display

---

### Task 5: 30-Day Forecast Breakdown

**Status:** Not Started  
**Estimated Effort:** 8 hours  
**Dependencies:** None

#### Description
Add a detailed 30-day forecast view showing day-by-day breakdown of sales, revenue, profit, and losses (not just monthly averages).

#### Technical Requirements

**Backend Changes:**
1. **API Endpoint:**
   - Update `GET /api/v1/stores/{store_id}/forecast` to support 30-day horizon
   - Add `GET /api/v1/stores/{store_id}/forecast-extended`:
     ```python
     class ExtendedForecastResponse(BaseModel):
         store_id: str
         forecast_period: str  # "30d"
         daily_forecasts: List[DailyForecastResponse]
         summary: ForecastSummaryResponse
     
     class DailyForecastResponse(BaseModel):
         date: str
         predicted_demand: float
         predicted_revenue: float
         predicted_profit: float
         predicted_loss: float  # From waste/expiry
         predicted_margin: float
         factors: Dict[str, Any]  # weather, holiday, etc.
     ```

2. **Service Updates:**
   - Update `ForecastingService` to generate 30-day forecasts
   - Add revenue/profit/loss calculations per day
   - Include waste/expiry predictions in loss calculations

3. **Loss Calculation:**
   - Create `services/api_gateway/loss_service.py`:
     ```python
     def calculate_predicted_losses(
         forecasted_demand: float,
         current_inventory: float,
         expiry_dates: List[date],
         shelf_life: int
     ) -> float:
         # Calculate expected waste from expiry
         # Calculate expected markdown losses
         # Return total predicted loss
     ```

**Frontend Changes:**
1. **Analytics Page Updates:**
   - Add "30-Day Forecast" tab to `AnalyticsPage.tsx`
   - Display day-by-day table:
     - Date
     - Forecasted Demand
     - Forecasted Revenue
     - Forecasted Profit
     - Forecasted Loss
     - Net Profit (Profit - Loss)
     - Margin %

2. **Visualizations:**
   - Line chart: Revenue, Profit, Loss over 30 days
   - Stacked area chart: Profit vs Loss
   - Bar chart: Daily margin %
   - Summary cards: Total revenue, profit, loss for 30 days

3. **Filtering:**
   - Filter by category
   - Filter by product
   - Filter by store (if multi-store)

4. **Export:**
   - Export 30-day forecast to CSV/Excel
   - Include all metrics per day

#### Acceptance Criteria
- [ ] API returns 30-day day-by-day forecast
- [ ] Frontend displays 30-day breakdown (not just averages)
- [ ] Shows revenue, profit, and loss per day
- [ ] Loss calculations include waste and markdowns
- [ ] Visualizations are clear and informative
- [ ] Filtering by category/product/store works
- [ ] Export functionality works
- [ ] Performance is acceptable (30-day forecast loads in <3 seconds)

#### Testing Requirements
- Unit tests for 30-day forecast generation
- Unit tests for loss calculations
- Integration tests for extended forecast API
- Frontend tests for 30-day forecast display

---

### Task 6: Loss Tracking and Display

**Status:** Not Started  
**Estimated Effort:** 6 hours  
**Dependencies:** Task 5 (30-Day Forecast)

#### Description
Add explicit loss tracking and display throughout the application. Show losses from waste, expiry, and markdowns separately.

#### Technical Requirements

**Backend Changes:**
1. **Database Schema:**
   - Add `losses` table (if not exists):
     ```python
     class Loss(Base):
         id = Column(Integer, primary_key=True)
         store_id = Column(Integer, ForeignKey("stores.id"))
         product_id = Column(Integer, ForeignKey("products.id"))
         loss_date = Column(Date)
         loss_type = Column(String)  # waste, expiry, markdown
         quantity = Column(Float)
         cost = Column(Float)  # Cost of lost items
         revenue_lost = Column(Float)  # Potential revenue lost
         created_at = Column(DateTime, default=datetime.utcnow)
     ```

2. **Loss Service:**
   - Create `services/api_gateway/loss_service.py`:
     ```python
     def calculate_daily_losses(
         store_id: str,
         target_date: date,
         db: Session
     ) -> Dict[str, float]:
         # Calculate:
         # - Waste losses (expired items discarded)
         # - Markdown losses (revenue lost from discounts)
         # - Total losses
     ```

3. **API Updates:**
   - Add loss metrics to `StoreStatsResponse`
   - Add `GET /api/v1/stores/{store_id}/losses` endpoint
   - Include losses in forecast responses

**Frontend Changes:**
1. **Dashboard:**
   - Add "Losses Today" KPI card
   - Show breakdown: Waste, Markdown, Total
   - Color: Red for losses

2. **Analytics Page:**
   - Add "Losses" section
   - Show loss trends over time
   - Breakdown by type (waste vs markdown)
   - Breakdown by category/product

3. **Inventory Page:**
   - Show potential losses for expiring items
   - "If not sold: $X loss"

#### Acceptance Criteria
- [ ] Loss tracking table exists
- [ ] Losses are calculated and stored
- [ ] Dashboard shows losses KPI
- [ ] Analytics shows loss trends
- [ ] Losses are broken down by type
- [ ] Forecast includes predicted losses
- [ ] Loss calculations are accurate

#### Testing Requirements
- Unit tests for loss calculations
- Integration tests for loss API
- Frontend tests for loss display

---

## 🟠 P1 - High Priority Features

### Task 7: Weather/Day/Holiday Factor Visibility

**Status:** Not Started  
**Estimated Effort:** 4 hours  
**Dependencies:** None

#### Description
Make the factors affecting forecasts (weather, day of week, holidays) visible in the UI so managers understand why forecasts are what they are.

#### Technical Requirements

**Backend Changes:**
1. **Forecast Response Enhancement:**
   - Update `ForecastResponse` to include factors:
     ```python
     class ForecastItem(BaseModel):
         date: str
         predicted_demand: float
         factors: ForecastFactorsResponse
     
     class ForecastFactorsResponse(BaseModel):
         weather: str  # "hot", "cold", "rainy", "normal"
         temperature: Optional[float]
         day_of_week: str
         is_weekend: bool
         is_holiday: bool
         holiday_name: Optional[str]
         seasonality_factor: float  # How much this affects demand
     ```

2. **Service Updates:**
   - Update `ForecastingService._generate_model_forecast` to include factors
   - Extract weather data from features
   - Extract calendar features

**Frontend Changes:**
1. **Forecast Display:**
   - Add "Factors" column/tooltip in forecast tables
   - Show icons: 🌤️ Weather, 📅 Day, 🎉 Holiday
   - Tooltip shows details: "Hot weather (+15% demand)", "Weekend (+20% demand)"

2. **Refill Dashboard:**
   - Show factors affecting tomorrow's forecast
   - Visual indicators for each factor

3. **Analytics:**
   - Add "Factor Impact" chart showing how factors affect demand
   - Show correlation: Weather vs Sales, Day of Week vs Sales

#### Acceptance Criteria
- [ ] Forecast responses include factor information
- [ ] Frontend displays factors clearly
- [ ] Icons/tooltips explain factor impact
- [ ] Managers can understand why forecasts are high/low
- [ ] Factor impact is quantified (e.g., "+15% due to hot weather")

#### Testing Requirements
- Unit tests for factor extraction
- Frontend tests for factor display

---

### Task 8: "At Cost Price" Discount Logic

**Status:** Not Started  
**Estimated Effort:** 5 hours  
**Dependencies:** None

#### Description
Enhance markdown recommendations to explicitly show "sell at cost price" option to avoid losses, with clear cost vs revenue calculations.

#### Technical Requirements

**Backend Changes:**
1. **Markdown Service Updates:**
   - Update `services/replenishment/markdown.py`:
     ```python
     def recommend_markdown(
         self,
         days_until_expiry: int,
         current_inventory: float,
         category_id: Optional[int] = None,
         cost_per_unit: Optional[float] = None
     ) -> Dict:
         # Calculate:
         # - Recommended discount to reach cost price
         # - Current price vs cost price
         # - Loss if not sold vs loss from discount
         # Return recommendation with "at_cost" flag
     ```

2. **API Updates:**
   - Update markdown response to include:
     - `cost_per_unit`
     - `current_price`
     - `discounted_price`
     - `at_cost_price` (boolean)
     - `potential_loss_if_not_sold`
     - `loss_from_discount`

**Frontend Changes:**
1. **Markdown Display:**
   - Show "Sell at Cost Price" badge for at-cost recommendations
   - Display: "Current: $X, Cost: $Y, Discount: Z% to reach cost"
   - Show comparison: "Loss if expired: $X vs Loss from discount: $Y"

2. **Inventory Page:**
   - Highlight items that should be sold at cost
   - Show cost price clearly
   - Add "Apply At-Cost Discount" button

#### Acceptance Criteria
- [ ] Markdown service calculates at-cost discounts
- [ ] API returns cost price information
- [ ] Frontend shows "at cost price" recommendations
- [ ] Loss comparisons are clear
- [ ] Managers can easily apply at-cost discounts

#### Testing Requirements
- Unit tests for at-cost discount calculations
- Integration tests for markdown API
- Frontend tests for at-cost display

---

### Task 9: Complete Ordering Workflow

**Status:** Not Started  
**Estimated Effort:** 10 hours  
**Dependencies:** Task 3 (Transit Time)

#### Description
Build a complete end-to-end ordering workflow from recommendation to delivery tracking.

#### Technical Requirements

**Backend Changes:**
1. **Order Management:**
   - Enhance `Order` model (from Task 3)
   - Add order status workflow: pending → approved → ordered → in_transit → delivered
   - Add `OrderLine` table for multi-product orders

2. **Order Service:**
   - Create `services/api_gateway/order_service.py`:
     ```python
     class OrderService:
         def create_order_from_recommendations(
             self,
             store_id: str,
             recommendations: List[Dict],
             order_date: date
         ) -> Order:
             # Create order from approved recommendations
         
         def track_order_status(
             self,
             order_id: int
         ) -> Dict:
             # Get current order status and tracking info
     ```

3. **API Endpoints:**
   - `POST /api/v1/orders` - Create order from recommendations
   - `GET /api/v1/orders/{order_id}` - Get order details
   - `PUT /api/v1/orders/{order_id}/status` - Update order status
   - `GET /api/v1/stores/{store_id}/orders` - Get store orders

**Frontend Changes:**
1. **Orders Page Enhancement:**
   - Add "Create Order" workflow:
     - Select recommendations
     - Review order summary
     - Confirm and create order
   - Order tracking view:
     - Show order status timeline
     - Show expected vs actual delivery
     - Update delivery status

2. **Order History:**
   - New page or section: "Order History"
   - Filter by date range, status
   - Show order details, delivery status

#### Acceptance Criteria
- [ ] Complete order workflow exists
- [ ] Orders can be created from recommendations
- [ ] Order status can be tracked
- [ ] Delivery dates are shown and updated
- [ ] Order history is accessible
- [ ] Multi-product orders are supported

#### Testing Requirements
- Unit tests for order service
- Integration tests for order API
- E2E test: Complete order workflow

---

### Task 10: Consistent Filtering Across Pages

**Status:** Not Started  
**Estimated Effort:** 6 hours  
**Dependencies:** None

#### Description
Implement consistent filtering (by category, product, store) across all pages that need it.

#### Technical Requirements

**Frontend Changes:**
1. **Shared Filter Component:**
   - Create `apps/store-manager-frontend/src/components/common/FilterBar.tsx`:
     ```typescript
     interface FilterBarProps {
       onCategoryChange: (category: string) => void
       onProductChange: (product: string) => void
       onStoreChange: (store: string) => void
       showStore?: boolean
       showProduct?: boolean
       showCategory?: boolean
     }
     ```

2. **Apply to Pages:**
   - Dashboard: Add category filter
   - Analytics: Enhance existing filters
   - Inventory: Add category/product filters
   - Products: Add category filter
   - Refill Dashboard: Add all filters

3. **Filter State Management:**
   - Use React Query for filter state
   - Persist filters in URL query params
   - Share filter state across pages (optional)

#### Acceptance Criteria
- [ ] Filter component is reusable
- [ ] All relevant pages have consistent filtering
- [ ] Filters work correctly
- [ ] Filter state persists (URL params)
- [ ] Performance is good with filters applied

#### Testing Requirements
- Component tests for FilterBar
- Integration tests for filtered views

---

### Task 11: Enhanced Forecast Insights Display

**Status:** Not Started  
**Estimated Effort:** 4 hours  
**Dependencies:** Task 7 (Factor Visibility)

#### Description
Improve the forecast insights section on the dashboard to be more informative and actionable.

#### Technical Requirements

**Frontend Changes:**
1. **Dashboard Forecast Section:**
   - Enhance `ForecastInsightsSection` in `DashboardPage.tsx`:
     - Show day-by-day breakdown for next 7 days (not just averages)
     - Add factors affecting each day
     - Show confidence intervals
     - Add "View Full Forecast" link to Analytics page

2. **Visual Improvements:**
   - Add mini charts for 7-day trend
   - Color code: High forecast (green), Low forecast (yellow)
   - Show variance from average

#### Acceptance Criteria
- [ ] Forecast insights show day-by-day for 7 days
- [ ] Factors are visible
- [ ] Visualizations are clear
- [ ] Links to detailed views work

---

### Task 12: Multi-Store View Enhancement

**Status:** Not Started  
**Estimated Effort:** 6 hours  
**Dependencies:** None

#### Description
Improve multi-store views for regional managers with better aggregation and comparison.

#### Technical Requirements

**Backend Changes:**
1. **Aggregation Endpoints:**
   - Enhance chain dashboard endpoints
   - Add store comparison metrics
   - Add ranking endpoints

**Frontend Changes:**
1. **Chain Dashboard:**
   - Add store comparison table
   - Add store ranking (by sales, profit, waste)
   - Add store selection for drill-down

#### Acceptance Criteria
- [ ] Multi-store views are enhanced
- [ ] Store comparison works
- [ ] Rankings are accurate
- [ ] Drill-down to individual stores works

---

### Task 13: Export Functionality Enhancement

**Status:** Not Started  
**Estimated Effort:** 4 hours  
**Dependencies:** None

#### Description
Add comprehensive export functionality (CSV/Excel) for all major views.

#### Technical Requirements

**Frontend Changes:**
1. **Export Service:**
   - Create `apps/store-manager-frontend/src/services/export.ts`:
     - Export to CSV
     - Export to Excel (using library like `xlsx`)
     - Export with formatting

2. **Add Export Buttons:**
   - Dashboard: Export KPIs
   - Analytics: Export forecasts
   - Inventory: Export inventory list
   - Refill Dashboard: Export refill plan
   - Orders: Export order history

#### Acceptance Criteria
- [ ] Export functionality exists for all major views
- [ ] CSV export works
- [ ] Excel export works (if implemented)
- [ ] Exported data is accurate and formatted

---

### Task 14: Mobile-Responsive Improvements

**Status:** Not Started  
**Estimated Effort:** 8 hours  
**Dependencies:** None

#### Description
Ensure all new and existing pages are fully mobile-responsive for tablet use in stores.

#### Technical Requirements

**Frontend Changes:**
1. **Responsive Design:**
   - Test all pages on mobile/tablet sizes
   - Adjust grid layouts for small screens
   - Make tables scrollable on mobile
   - Optimize touch targets

2. **Mobile-Specific Features:**
   - Collapsible navigation
   - Bottom navigation (optional)
   - Swipe gestures (optional)

#### Acceptance Criteria
- [ ] All pages work on mobile/tablet
- [ ] Tables are scrollable
- [ ] Touch targets are adequate
- [ ] Navigation is mobile-friendly

---

## 🟡 P2 - Medium Priority Features

### Task 15: Advanced Analytics - Trend Analysis

**Status:** Not Started  
**Estimated Effort:** 6 hours  
**Dependencies:** None

#### Description
Add advanced analytics: trend analysis, seasonality detection, anomaly detection.

#### Technical Requirements

**Backend Changes:**
1. **Analytics Service:**
   - Create `services/api_gateway/analytics_service.py`:
     - Trend detection
     - Seasonality analysis
     - Anomaly detection

**Frontend Changes:**
1. **Analytics Page:**
   - Add "Trends" section
   - Show trend indicators
   - Highlight anomalies

#### Acceptance Criteria
- [ ] Trend analysis works
- [ ] Anomalies are detected
- [ ] Visualizations are clear

---

### Task 16: Product Performance Deep Dive

**Status:** Not Started  
**Estimated Effort:** 5 hours  
**Dependencies:** None

#### Description
Add detailed product performance analysis with recommendations.

#### Technical Requirements

**Frontend Changes:**
1. **Product Detail Page:**
   - Sales history
   - Forecast accuracy
   - Profitability analysis
   - Recommendations

#### Acceptance Criteria
- [ ] Product deep dive page exists
- [ ] All metrics are shown
- [ ] Recommendations are actionable

---

### Task 17: Scenario Simulation Enhancement

**Status:** Not Started  
**Estimated Effort:** 6 hours  
**Dependencies:** None

#### Description
Enhance the scenario simulation feature in Streamlit dashboard and add to main app.

#### Technical Requirements

**Frontend Changes:**
1. **Simulation Page:**
   - "What if" scenarios
   - Weather changes
   - Holiday effects
   - Promotion effects

#### Acceptance Criteria
- [ ] Simulation feature works
- [ ] Scenarios are realistic
- [ ] Results are clear

---

### Task 18: Automated Reporting

**Status:** Not Started  
**Estimated Effort:** 8 hours  
**Dependencies:** None

#### Description
Add automated daily/weekly reports sent via email.

#### Technical Requirements

**Backend Changes:**
1. **Report Service:**
   - Create `services/api_gateway/report_service.py`
   - Generate PDF reports
   - Email integration

2. **Scheduled Jobs:**
   - Daily reports
   - Weekly summaries

#### Acceptance Criteria
- [ ] Reports are generated
- [ ] Email delivery works
- [ ] Reports are accurate

---

## 🟢 P3 - Low Priority / Future Enhancements

### Task 19: WebSocket Real-Time Updates

**Status:** Not Started  
**Estimated Effort:** 12 hours  
**Dependencies:** Task 4 (Notifications)

#### Description
Implement WebSocket for real-time updates instead of polling.

#### Technical Requirements

**Backend Changes:**
1. **WebSocket Server:**
   - FastAPI WebSocket support
   - Real-time notification delivery

**Frontend Changes:**
1. **WebSocket Client:**
   - Connect to WebSocket
   - Handle real-time updates

---

### Task 20: Advanced ML Features

**Status:** Not Started  
**Estimated Effort:** 16 hours  
**Dependencies:** None

#### Description
Add advanced ML features: demand clustering, price elasticity, dynamic pricing.

#### Technical Requirements

**Backend Changes:**
1. **ML Services:**
   - Demand clustering
   - Price elasticity models
   - Dynamic pricing algorithms

---

### Task 21: Integration with External Systems

**Status:** Not Started  
**Estimated Effort:** 20 hours  
**Dependencies:** None

#### Description
Add integrations with POS systems, ERP, WMS.

#### Technical Requirements

**Backend Changes:**
1. **Integration Services:**
   - POS integration
   - ERP integration
   - WMS integration
   - API adapters

---

## 📅 Implementation Timeline

### Phase 1: Critical Features (Weeks 1-3)
- Task 1: Shelf vs Stock Separation
- Task 2: Refill Dashboard
- Task 3: Transit Time Integration
- Task 4: Real-Time Notifications
- Task 5: 30-Day Forecast
- Task 6: Loss Tracking

### Phase 2: High Priority (Weeks 4-6)
- Task 7: Factor Visibility
- Task 8: At-Cost Discounts
- Task 9: Ordering Workflow
- Task 10: Consistent Filtering
- Task 11: Enhanced Forecast Insights
- Task 12: Multi-Store Enhancement
- Task 13: Export Enhancement
- Task 14: Mobile Responsive

### Phase 3: Medium Priority (Weeks 7-8)
- Task 15: Advanced Analytics
- Task 16: Product Deep Dive
- Task 17: Scenario Simulation
- Task 18: Automated Reporting

### Phase 4: Future Enhancements (Ongoing)
- Task 19: WebSocket
- Task 20: Advanced ML
- Task 21: External Integrations

---

## 🔧 Technical Considerations

### Database Migrations
- All schema changes require migration scripts
- Use Alembic for migrations
- Test migrations on sample data

### API Versioning
- New endpoints should be versioned
- Maintain backward compatibility where possible

### Performance
- Optimize database queries
- Add caching where appropriate
- Consider pagination for large datasets

### Testing
- Minimum 80% code coverage
- Unit tests for all new services
- Integration tests for API endpoints
- E2E tests for critical workflows

### Documentation
- Update API documentation
- Update user documentation
- Add code comments for complex logic

---

## ✅ Definition of Done

Each task is considered complete when:
1. All acceptance criteria are met
2. Code is reviewed and approved
3. Tests are written and passing
4. Documentation is updated
5. Feature is tested in staging environment
6. No critical bugs remain

---

## 📝 Notes

- Tasks should be broken down into smaller subtasks during implementation
- Daily standups recommended to track progress
- Blockers should be escalated immediately
- Estimated effort is in hours and may vary based on complexity

---

**Next Steps:**
1. Review and prioritize tasks
2. Assign tasks to developers
3. Set up project board/tracking
4. Begin Phase 1 implementation

