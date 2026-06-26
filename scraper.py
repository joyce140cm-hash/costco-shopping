from playwright.sync_api import sync_playwright
import json
from datetime import datetime
import re

BAD_TEXT = ['加入購物車', '購物車', '加入', '比較', '願望清單', 'Quick View',
            '登入', '會員', '查看更多', 'Loading', '載入中']

def is_bad_name(text):
    if not text:
        return True
    if len(text) < 2 or len(text) > 120:
        return True
    for bad in BAD_TEXT:
        if bad in text:
            return True
    # 全是符號或星號開頭的法律聲明
    if text.startswith('*') and len(text) > 30:
        return True
    return False

def clean_price(text):
    if not text:
        return None
    nums = re.findall(r'[\d,]+', text)
    if nums:
        val = int(nums[0].replace(',', ''))
        if 10 <= val <= 1000000:  # 合理價格範圍
            return val
    return None

def scrape_page(page, url, category_name, online_only=False):
    products = []
    try:
        page.goto(url, timeout=60000, wait_until='domcontentloaded')
        page.wait_for_timeout(6000)
        try:
            page.wait_for_load_state('networkidle', timeout=15000)
        except Exception:
            pass

        # 用 JavaScript 直接從 DOM 萃取商品資料，避免誤抓按鈕文字
        results = page.evaluate('''
        () => {
            const results = [];

            // 先嘗試常見的商品 tile selector
            const selectors = [
                '.product-tile', '[class*="ProductTile"]', '[class*="product-tile"]',
                '.product-card', '[class*="ProductCard"]', '[class*="product-card"]',
                '[data-product-id]', '[data-item-number]',
                'li[class*="product"]', 'article[class*="product"]',
                '.gallery-item', '[class*="gallery-item"]'
            ];

            let tiles = [];
            let usedSel = '';
            for (const sel of selectors) {
                tiles = Array.from(document.querySelectorAll(sel));
                if (tiles.length > 2) { usedSel = sel; break; }
            }

            console.log('Used selector:', usedSel, '| tiles found:', tiles.length);

            for (const tile of tiles.slice(0, 40)) {
                let name = null, price = null, img = null, link = null;

                // ① 品名：優先找 <a> 連結文字（商品連結），排除按鈕
                const links = tile.querySelectorAll('a[href]');
                for (const a of links) {
                    const t = a.textContent.trim().replace(/\\s+/g, ' ');
                    // 商品連結通常有 href 且不是純圖示/按鈕
                    if (t.length > 3 && t.length < 120 &&
                        !t.includes('加入') && !t.includes('購物車') && !t.startsWith('*')) {
                        name = t;
                        link = a.href;
                        break;
                    }
                }

                // ② 若無連結，試找 h2/h3/h4
                if (!name) {
                    const hEl = tile.querySelector('h2,h3,h4');
                    if (hEl) {
                        const t = hEl.textContent.trim().replace(/\\s+/g, ' ');
                        if (t.length > 3 && t.length < 120 && !t.includes('加入')) name = t;
                    }
                }

                // ③ 試找帶 title/name class 的 span/div
                if (!name) {
                    const nameEl = tile.querySelector(
                        '[class*="name"],[class*="title"],[class*="description"],[class*="Name"],[class*="Title"]'
                    );
                    if (nameEl && nameEl.tagName !== 'BUTTON') {
                        const t = nameEl.textContent.trim().replace(/\\s+/g, ' ');
                        if (t.length > 3 && t.length < 120 && !t.includes('加入')) name = t;
                    }
                }

                // ④ 價格
                const allEls = tile.querySelectorAll('*');
                for (const el of allEls) {
                    if (el.children.length > 0) continue;
                    const t = el.textContent.trim();
                    const m = t.match(/NT\\$?\\s*([\\d,]+)/);
                    if (m) {
                        const v = parseInt(m[1].replace(/,/g,''));
                        if (v >= 10 && v <= 1000000) { price = v; break; }
                    }
                }

                // ⑤ 圖片 + alt 當品名備用
                const imgEl = tile.querySelector('img');
                if (imgEl) {
                    img = imgEl.src || imgEl.dataset.src || imgEl.dataset.lazySrc || null;
                    if (img && img.startsWith('data:')) img = imgEl.dataset.src || null;
                    // img alt 通常是商品名
                    if (!name && imgEl.alt && imgEl.alt.trim().length > 3) {
                        const altText = imgEl.alt.trim();
                        if (!altText.includes('加入') && !altText.startsWith('*')) {
                            name = altText;
                        }
                    }
                }

                if (name && name.length > 2) {
                    results.push({ name, price, img, link });
                }
            }

            return { results, tileCount: tiles.length, selector: usedSel };
        }
        ''')

        print(f"  selector={results.get('selector','?')} tiles={results.get('tileCount',0)} 商品={len(results.get('results',[]))}")
        for item in results.get('results', []):
            entry = {
                'name': item['name'],
                'price': item.get('price'),
                'image': item.get('img'),
                'link': item.get('link'),
                'category': category_name,
            }
            if online_only:
                entry['online_only'] = True
            products.append(entry)

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
            viewport={'width': 1280, 'height': 900},
        )
        page = context.new_page()

        print("正在抓取優惠券 / 月刊特價...")
        coupons = scrape_page(page, 'https://www.costco.com.tw/Deals/c/Coupon', '優惠券特價')
        print(f"  → {len(coupons)} 筆")

        print("正在抓取新品上市...")
        new_items = scrape_page(page, 'https://www.costco.com.tw/c/whats-new', '新品上市')
        print(f"  → {len(new_items)} 筆")

        print("正在抓取限時優惠...")
        hot_buys = scrape_page(page, 'https://www.costco.com.tw/c/hot-buys', '限時優惠', online_only=True)
        print(f"  → {len(hot_buys)} 筆")

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
    print(f"\n完成！共抓到 {total} 筆，已存至 deals.json")


if __name__ == '__main__':
    main()
