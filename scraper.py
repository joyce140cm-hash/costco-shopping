from playwright.sync_api import sync_playwright
import json
from datetime import datetime
import re


def clean_price(text):
    if not text:
        return None
    nums = re.findall(r'[\d,]+', text)
    if nums:
        return int(nums[0].replace(',', ''))
    return None


def scrape_page(page, url, category_name, online_only=False):
    products = []
    try:
        page.goto(url, timeout=60000, wait_until='domcontentloaded')
        # 等待更久讓 JS 渲染完成
        page.wait_for_timeout(5000)
        try:
            page.wait_for_load_state('networkidle', timeout=15000)
        except Exception:
            pass

        # 嘗試多種 selector（好市多 TW 可能用不同 class）
        selectors = [
            '.product-tile',
            '[data-testid="product-tile"]',
            '.product-card',
            '.product',
            '[class*="ProductTile"]',
            '[class*="product-tile"]',
            '[class*="ProductCard"]',
            '[class*="product-card"]',
            '[data-product-id]',
            '[data-item-number]',
            'article[class*="product"]',
            'li[class*="product"]',
            '.gallery-item',
            '[class*="gallery-item"]',
        ]

        tiles = []
        for sel in selectors:
            tiles = page.query_selector_all(sel)
            if tiles:
                print(f"  找到 selector: {sel} ({len(tiles)} 筆)")
                break

        if not tiles:
            print(f"  找不到商品 tile，嘗試尋找含價格元素...")
            price_els = page.query_selector_all('[class*="price"]')
            print(f"  含 price 的元素：{len(price_els)} 個")

        for tile in tiles[:30]:
            try:
                name_el = (
                    tile.query_selector('.description') or
                    tile.query_selector('[class*="description"]') or
                    tile.query_selector('.product-title') or
                    tile.query_selector('[class*="title"]') or
                    tile.query_selector('h2') or
                    tile.query_selector('h3') or
                    tile.query_selector('h4') or
                    tile.query_selector('p')
                )
                price_el = (
                    tile.query_selector('.price') or
                    tile.query_selector('[class*="price"]') or
                    tile.query_selector('[class*="Price"]')
                )
                img_el = tile.query_selector('img')

                name = name_el.inner_text().strip() if name_el else None
                price = clean_price(price_el.inner_text() if price_el else None)
                img = img_el.get_attribute('src') if img_el else None
                if img_el and (not img or img.startswith('data:')):
                    img = (img_el.get_attribute('data-src') or
                           img_el.get_attribute('data-lazy-src') or
                           img_el.get_attribute('data-original'))

                if name and len(name) > 2:
                    item = {
                        'name': name,
                        'price': price,
                        'image': img,
                        'category': category_name,
                    }
                    if online_only:
                        item['online_only'] = True
                    products.append(item)
            except Exception:
                continue

    except Exception as e:
        print(f"無法載入 {url}: {e}")

    return products


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/124.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 800},
        )
        page = context.new_page()

        print("正在抓取優惠券 / 月刊特價（全台門市適用）...")
        coupons = scrape_page(page, 'https://www.costco.com.tw/Deals/c/Coupon', '優惠券特價')
        print(f"  → 抓到 {len(coupons)} 筆")

        print("正在抓取新品上市...")
        new_items = scrape_page(page, 'https://www.costco.com.tw/c/whats-new', '新品上市')
        print(f"  → 抓到 {len(new_items)} 筆")

        print("正在抓取限時優惠（僅限線上購物）...")
        hot_buys = scrape_page(page, 'https://www.costco.com.tw/c/hot-buys', '限時優惠', online_only=True)
        print(f"  → 抓到 {len(hot_buys)} 筆")

        browser.close()

    result = {
        'updated': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'note': '優惠券/新品：全台門市（含中和店）適用。限時優惠：僅限線上購物。',
        'coupons': coupons,
        'new_items': new_items,
        'hot_buys': hot_buys,
    }

    with open('deals.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    total = len(coupons) + len(new_items) + len(hot_buys)
    print(f"\n完成！共抓到 {total} 筆資料，已存至 deals.json")


if __name__ == '__main__':
    main()
