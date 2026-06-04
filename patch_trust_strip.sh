sed -i '' -e '/<div class="pl-trust-strip"/,/<\/div>/c\
                <div class="pl-trust-strip" aria-label="Product trust signals">\
                  <span class="pl-trust-strip__item">\
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="icon icon-badge"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 1 8.3C18.4 15 15.1 20 11 20z"/><path d="M11 20c2.8-2 3.64-5.36 4.2-8.3"/></svg>\
                    100% Certified Organic\
                  </span>\
                  <span class="pl-trust-strip__item">\
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="icon icon-badge"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="M9 12l2 2 4-4"/></svg>\
                    Sustainably Sourced\
                  </span>\
                  <span class="pl-trust-strip__item">\
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="icon icon-badge"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>\
                    Secure Checkout\
                  </span>\
                </div>\
' sections/main-product.liquid
