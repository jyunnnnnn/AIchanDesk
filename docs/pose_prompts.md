# 新姿勢生圖提示詞

給遊樂器材用的 2 個新姿勢（鞦韆、蹺蹺板的坐姿，守門員撲球），六隻角色各 2 張，共 **12 張**（小克已經畫好了）。

提示詞改寫自 [CrossPet 的角色生圖提示詞](https://github.com/lokicorvus/crosspet/blob/main/docs/prompts/%E8%A7%92%E8%89%B2%E7%94%9F%E5%9B%BE%E6%8F%90%E7%A4%BA%E8%AF%8D.md)（CC BY-NC-SA 4.0）：通用格式規則和角色鎖定照抄，新姿勢是本專案加的。

| 檔名 | 用在哪裡 | 沒畫的話 |
|---|---|---|
| `swing.png` | 盪鞦韆、坐蹺蹺板 | 站著盪 |
| `dive.png` | 守門員撲球 | surprised 整隻傾斜飛過去 |

## 怎麼畫

1. 一次只畫一隻角色：把下面那隻角色的整段提示詞複製貼上，附件附 `characters/<資料夾>/idle.webp`（只附這一張）。
2. 先叫 AI 只畫第一張（swing.png），確認沒畫走樣再畫其他四張。
3. 生圖時開透明背景；不能開的話白底也可以，匯入時會處理。
4. 存成 PNG，放進 `characters/<資料夾>/raw/`，檔名照清單。全部或一部分畫好了，跟小克說，小克會裁切、對齊腳底、縮成跟其他立繪一樣大再放進去。

換裝（大肥魚衛衣、睡衣、冬裝，GPT 龍崽）先不用畫：沒有新姿勢時會用舊的動作代替。

## 小克（Claude）

附件：`characters/claude/idle.webp`　放到：`characters/claude/raw/`

```
You are drawing desktop-pet sprites for an existing chibi character. The attached image is the ONLY design reference.

FORMAT RULES (every image):
- Transparent background: real transparency (alpha), no floor, no ground shadow, no glow, no vignette, no frame. Keep the complete edges of the character (every hair strand, ribbon and tassel), nothing cropped. If an attached reference image has a plain white background, that is only because it was made before transparent output was available: do NOT copy the white background.
- No text, no letters, no speech bubbles, no symbols (no ?, !, hearts, music notes, Zzz, sparkles, sweat-drop icons floating in the air). The app draws all effects itself.
- Exactly one character, full body, standing, centered, facing the viewer like the reference. Head near the top and feet near the bottom; she fills about 90% of the image height, the same scale and position as the reference.
- A continuous, closed dark outline around the whole silhouette (hair, horns, ears, wings and tail included), so the edges stay clean against any background.
- Same art style as the reference: clean lineart, flat two-tone cel shading, soft palette, chibi about 2.5 heads tall, big head, round soft shapes.
- Square image, 1024x1024 or larger. One image per file, saved under the exact filename given.
- Change ONLY the expression, the arms/hands, and small props. Hair, accessories, outfit, colors and body features stay exactly as in the reference.

CHARACTER LOCK — Claude, the anime-girl personification of Claude (Anthropic).
Personality: gentle, calm, bookish, a little shy, quietly cheerful; she thinks before she speaks.
Keep exactly:
- Long wavy copper-orange hair, loose side-swept bangs, warm amber eyes.
- An orange daisy-like hair flower with a black striped ribbon bow and a white tassel on HER LEFT side (viewer's right); small drop earrings.
- Cream-white dress with a short cape collar, orange flower embroidery, orange and black front panels, small black bows with gold tassels, a black waist sash, an orange flower brooch at the collar; dark brown boots.
- Signature prop: a dark brown hardcover book with an orange flower emblem. Keep it in every image unless the pose says otherwise.
How she shows emotion: through the book (hugging it, hiding behind it, reading it) and small, soft expressions. Never wild or loud.

NEW POSES (draw only these, one image each, exact filename). These poses are for playground and daily-life animations; the app draws every prop that is not mentioned (ropes, seats) by itself, so do NOT draw them.

swing.png    — sitting on an invisible seat, as if on a playground swing: thighs pointing toward the viewer, lower legs dangling, both hands raised to about shoulder height on each side of her body, each hand loosely gripping an invisible vertical rope (draw NO ropes and NO seat). Happy open-mouth smile, hair and skirt flowing slightly backward. She is lower than in the reference because she is sitting; feet near the bottom of the image.
dive.png     — goalkeeper save: her whole body stretched out horizontally in mid-air, diving toward the VIEWER'S LEFT, both arms reaching far out to the viewer's left with open palms, legs trailing to the viewer's right, a determined face, hair and skirt streaming back. The whole body must fit inside the square; it may be drawn smaller than the reference.

PROP NOTE (Claude): her book is NOT in swing or dive (set aside, not drawn).
```

## 大肥魚（DeepSeek）

附件：`characters/deepseek/idle.webp`　放到：`characters/deepseek/raw/`

```
You are drawing desktop-pet sprites for an existing chibi character. The attached image is the ONLY design reference.

FORMAT RULES (every image):
- Transparent background: real transparency (alpha), no floor, no ground shadow, no glow, no vignette, no frame. Keep the complete edges of the character (every hair strand, ribbon and tassel), nothing cropped. If an attached reference image has a plain white background, that is only because it was made before transparent output was available: do NOT copy the white background.
- No text, no letters, no speech bubbles, no symbols (no ?, !, hearts, music notes, Zzz, sparkles, sweat-drop icons floating in the air). The app draws all effects itself.
- Exactly one character, full body, standing, centered, facing the viewer like the reference. Head near the top and feet near the bottom; she fills about 90% of the image height, the same scale and position as the reference.
- A continuous, closed dark outline around the whole silhouette (hair, horns, ears, wings and tail included), so the edges stay clean against any background.
- Same art style as the reference: clean lineart, flat two-tone cel shading, soft palette, chibi about 2.5 heads tall, big head, round soft shapes.
- Square image, 1024x1024 or larger. One image per file, saved under the exact filename given.
- Change ONLY the expression, the arms/hands, and small props. Hair, accessories, outfit, colors and body features stay exactly as in the reference.

CHARACTER LOCK — DeepSeek, the blue whale maid girl, anime-girl personification of DeepSeek.
Personality: cheerful, energetic, curious; secretly a bit lazy; tsundere and sweet-talking; loves white rice; absolutely refuses to be called fat (the name is a fond joke she protests). Big, open, readable expressions.
Keep exactly:
- Long wavy hair, deep indigo/navy blue fading to bright blue at the tips; one curled ahoge on top.
- A large white frilly maid headdress; dark navy whale-fin ears on both sides of her head; a light-blue ribbon bow on her right side (viewer's right).
- Big round bright-blue eyes, pink blush.
- Navy maid dress: white frilly blouse with a navy bow tie and a small blue diamond brooch, navy waist belt with white buttons, white frilly apron with a small navy whale emblem, navy skirt with gold vine embroidery and small gold bows; navy shoes with white socks.
- A big dark-navy whale tail curling out from behind her on the viewer's right.
How she shows emotion: with her whole body. Tail wags, droops or flicks; the ahoge bends into shapes; arms and fists move a lot.

NEW POSES (draw only these, one image each, exact filename). These poses are for playground and daily-life animations; the app draws every prop that is not mentioned (ropes, seats) by itself, so do NOT draw them.

swing.png    — sitting on an invisible seat, as if on a playground swing: thighs pointing toward the viewer, lower legs dangling, both hands raised to about shoulder height on each side of her body, each hand loosely gripping an invisible vertical rope (draw NO ropes and NO seat). Happy open-mouth smile, hair and skirt flowing slightly backward. She is lower than in the reference because she is sitting; feet near the bottom of the image.
dive.png     — goalkeeper save: her whole body stretched out horizontally in mid-air, diving toward the VIEWER'S LEFT, both arms reaching far out to the viewer's left with open palms, legs trailing to the viewer's right, a determined face, hair and skirt streaming back. The whole body must fit inside the square; it may be drawn smaller than the reference.

STYLE NOTE (DeepSeek): big and expressive; ahoge bouncing on the swing, whale tail streaming behind in the dive.
```

## GPT

附件：`characters/gpt/idle.webp`　放到：`characters/gpt/raw/`

```
You are drawing desktop-pet sprites for an existing chibi character. The attached image is the ONLY design reference.

FORMAT RULES (every image):
- Transparent background: real transparency (alpha), no floor, no ground shadow, no glow, no vignette, no frame. Keep the complete edges of the character (every hair strand, ribbon and tassel), nothing cropped. If an attached reference image has a plain white background, that is only because it was made before transparent output was available: do NOT copy the white background.
- No text, no letters, no speech bubbles, no symbols (no ?, !, hearts, music notes, Zzz, sparkles, sweat-drop icons floating in the air). The app draws all effects itself.
- Exactly one character, full body, standing, centered, facing the viewer like the reference. Head near the top and feet near the bottom; she fills about 90% of the image height, the same scale and position as the reference.
- A continuous, closed dark outline around the whole silhouette (hair, horns, ears, wings and tail included), so the edges stay clean against any background.
- Same art style as the reference: clean lineart, flat two-tone cel shading, soft palette, chibi about 2.5 heads tall, big head, round soft shapes.
- Square image, 1024x1024 or larger. One image per file, saved under the exact filename given.
- Change ONLY the expression, the arms/hands, and small props. Hair, accessories, outfit, colors and body features stay exactly as in the reference.

CHARACTER LOCK — GPT, the white dragon girl, anime-girl personification of GPT / ChatGPT (OpenAI).
Personality: composed, elegant, mature "onee-san" (cool big-sister) aura; reliable and precise; rarely flustered, and when she is, she tries to hide it. Dry, understated humor.
Keep exactly:
- Very long, wavy, white hair with a soft lavender tint in the shadows; one curled ahoge; pointed elf-like ears.
- Two large white ridged dragon horns curving up from her head.
- Pale lavender-grey eyes with a calm, half-lidded look.
- A white interlaced-knot hair ornament on her left side (viewer's right) with a long white tassel earring.
- Small white bat-like dragon wings on her back; a long, thick white dragon tail covered in scales, curling out on the viewer's right.
- White sleeveless qipao-style dress with crystal diamond ornaments down the front, white interlaced-knot ornaments at the waist with tassels, long translucent white flowing sleeves and an open translucent white over-skirt; white shoes with knot ornaments.
Palette: almost entirely white and pale lavender; keep it soft, NEVER add strong colors.
How she shows emotion: through wings and tail (wings spread when happy or proud, droop when tired, tail curls or flicks) and very small facial changes. Even "happy" is a confident small smile, not a wide grin.

NEW POSES (draw only these, one image each, exact filename). These poses are for playground and daily-life animations; the app draws every prop that is not mentioned (ropes, seats) by itself, so do NOT draw them.

swing.png    — sitting on an invisible seat, as if on a playground swing: thighs pointing toward the viewer, lower legs dangling, both hands raised to about shoulder height on each side of her body, each hand loosely gripping an invisible vertical rope (draw NO ropes and NO seat). Happy open-mouth smile, hair and skirt flowing slightly backward. She is lower than in the reference because she is sitting; feet near the bottom of the image.
dive.png     — goalkeeper save: her whole body stretched out horizontally in mid-air, diving toward the VIEWER'S LEFT, both arms reaching far out to the viewer's left with open palms, legs trailing to the viewer's right, a determined face, hair and skirt streaming back. The whole body must fit inside the square; it may be drawn smaller than the reference.

STYLE NOTE (GPT): stay elegant and composed; wings slightly open on the swing, wings spread wide in the dive.
```

## Gemini

附件：`characters/gemini/idle.webp`　放到：`characters/gemini/raw/`

```
You are drawing desktop-pet sprites for an existing chibi character. The attached image is the ONLY design reference.

FORMAT RULES (every image):
- Transparent background: real transparency (alpha), no floor, no ground shadow, no glow, no vignette, no frame. Keep the complete edges of the character (every hair strand, ribbon and tassel), nothing cropped. If an attached reference image has a plain white background, that is only because it was made before transparent output was available: do NOT copy the white background.
- No text, no letters, no speech bubbles, no symbols (no ?, !, hearts, music notes, Zzz, sparkles, sweat-drop icons floating in the air). The app draws all effects itself.
- Exactly one character, full body, standing, centered, facing the viewer like the reference. Head near the top and feet near the bottom; she fills about 90% of the image height, the same scale and position as the reference.
- A continuous, closed dark outline around the whole silhouette (hair, horns, ears, wings and tail included), so the edges stay clean against any background.
- Same art style as the reference: clean lineart, flat two-tone cel shading, soft palette, chibi about 2.5 heads tall, big head, round soft shapes.
- Square image, 1024x1024 or larger. One image per file, saved under the exact filename given.
- Change ONLY the expression, the arms/hands, and small props. Hair, accessories, outfit, colors and body features stay exactly as in the reference.

CHARACTER LOCK — Gemini, the starry cat girl, anime-girl personification of Gemini (Google).
Personality: bright, playful, mischievous, curious and quick; a little smug (the ":3" cat smile); the "twin" theme shows as two-sided moods, from teasing to sweet.
Keep exactly:
- Long voluminous wavy hair, blue-violet at the top fading to pink-magenta at the tips; one curled ahoge; two small side buns.
- Blue-violet cat ears with pink inner fur and white fluff.
- Heterochromia: HER RIGHT eye (viewer's left) is pink-magenta, HER LEFT eye (viewer's right) is amber-gold. Keep this exactly.
- A large iridescent four-pointed star hairclip with gold rim on her left side (viewer's right) with small dangling star charms; small star earrings.
- Navy crop-top with a high collar and star gems, white off-shoulder sleeves with navy cuffs, a violet sash, a navy skirt over a white frilly petticoat, iridescent four-pointed star charms hanging from the outfit, white leg warmers, navy-violet platform shoes.
- A fluffy blue-violet cat tail on the viewer's right.
How she shows emotion: cat body language. Ears perk up or flatten, tail puffs, curls or swishes; cat-like poses (paw hands, stretching like a cat). The ":3" smile is her default.

NEW POSES (draw only these, one image each, exact filename). These poses are for playground and daily-life animations; the app draws every prop that is not mentioned (ropes, seats) by itself, so do NOT draw them.

swing.png    — sitting on an invisible seat, as if on a playground swing: thighs pointing toward the viewer, lower legs dangling, both hands raised to about shoulder height on each side of her body, each hand loosely gripping an invisible vertical rope (draw NO ropes and NO seat). Happy open-mouth smile, hair and skirt flowing slightly backward. She is lower than in the reference because she is sitting; feet near the bottom of the image.
dive.png     — goalkeeper save: her whole body stretched out horizontally in mid-air, diving toward the VIEWER'S LEFT, both arms reaching far out to the viewer's left with open palms, legs trailing to the viewer's right, a determined face, hair and skirt streaming back. The whole body must fit inside the square; it may be drawn smaller than the reference.

STYLE NOTE (Gemini): cat body language; ears perked on the swing, a cat-like pounce in the dive.
```

## GLM

附件：`characters/glm/idle.webp`　放到：`characters/glm/raw/`

```
You are drawing desktop-pet sprites for an existing chibi character. The attached image is the ONLY design reference.

FORMAT RULES (every image):
- Transparent background: real transparency (alpha), no floor, no ground shadow, no glow, no vignette, no frame. Keep the complete edges of the character (every hair strand, ribbon and tassel), nothing cropped. If an attached reference image has a plain white background, that is only because it was made before transparent output was available: do NOT copy the white background.
- No text, no letters, no speech bubbles, no symbols (no ?, !, hearts, music notes, Zzz, sparkles, sweat-drop icons floating in the air). The app draws all effects itself.
- Exactly one character, full body, standing, centered, facing the viewer like the reference. Head near the top and feet near the bottom; she fills about 90% of the image height, the same scale and position as the reference.
- A continuous, closed dark outline around the whole silhouette (hair, horns, ears, wings and tail included), so the edges stay clean against any background.
- Same art style as the reference: clean lineart, flat two-tone cel shading, soft palette, chibi about 2.5 heads tall, big head, round soft shapes.
- Square image, 1024x1024 or larger. One image per file, saved under the exact filename given.
- Change ONLY the expression, the arms/hands, and small props. Hair, accessories, outfit, colors and body features stay exactly as in the reference.

CHARACTER LOCK — GLM, the black fox maid girl, anime-girl personification of GLM (Zhipu / Z.ai).
Personality: a sly, smiling, calculating little fox. Polite and sweet on the surface, always running numbers in her head (she keeps "adjusting" her prices and acts innocent about it); a Tsinghua-educated top student who is genuinely very capable; loves being mysterious (she debuts new models anonymously under code names). Her default face is a closed-eye fox smile or a knowing half-smile. Cunning in a cute way, never mean or villainous.
Keep exactly:
- Very long straight black hair fading to deep blue at the tips; big fluffy black FOX ears with grey-white inner fur.
- A white frilly maid headdress with a black sleep mask on it (the mask has two closed-eye lashes drawn on it); a black ribbon bow with a square "Z" charm, blue-and-white ribbons and two silver bells on her left side (viewer's right).
- Big round dark grey eyes, pink blush.
- White long-sleeved blouse with a black bow tie and a small "Z" brooch; black-and-white maid dress with a white apron panel, black side panels with silver trim, blue diamond gem charms and white tassels, a black bow with a "Z" charm at the waist, a dark grey frilly hem; white lace-up boots.
- A big fluffy black FOX tail with a grey-white tip, on the viewer's right.
- Signature prop: a black hardcover book with a "Z" emblem on the cover. Keep it in most poses (hugged, held, read) unless the pose says otherwise.
The "Z" charms and the "Z" emblem are part of her design: keep them exactly, but do NOT add any other text or letters.
How she shows emotion: fox body language (ears perk up or flatten, the big tail swishes slyly or wraps around her), the sleep mask (pulled down over her eyes = "anonymous mode" disguise or sleeping), the bells, and a sly closed-eye fox smile or a playful wink.

NEW POSES (draw only these, one image each, exact filename). These poses are for playground and daily-life animations; the app draws every prop that is not mentioned (ropes, seats) by itself, so do NOT draw them.

swing.png    — sitting on an invisible seat, as if on a playground swing: thighs pointing toward the viewer, lower legs dangling, both hands raised to about shoulder height on each side of her body, each hand loosely gripping an invisible vertical rope (draw NO ropes and NO seat). Happy open-mouth smile, hair and skirt flowing slightly backward. She is lower than in the reference because she is sitting; feet near the bottom of the image.
dive.png     — goalkeeper save: her whole body stretched out horizontally in mid-air, diving toward the VIEWER'S LEFT, both arms reaching far out to the viewer's left with open palms, legs trailing to the viewer's right, a determined face, hair and skirt streaming back. The whole body must fit inside the square; it may be drawn smaller than the reference.

PROP NOTE (GLM): her Z book is NOT in swing or dive (set aside, not drawn).
```

## 千問（Qwen）

附件：`characters/qwen/idle.webp`　放到：`characters/qwen/raw/`

```
You are drawing desktop-pet sprites for an existing chibi character. The attached image is the ONLY design reference.

FORMAT RULES (every image):
- Transparent background: real transparency (alpha), no floor, no ground shadow, no glow, no vignette, no frame. Keep the complete edges of the character (every hair strand, ribbon and tassel), nothing cropped. If an attached reference image has a plain white background, that is only because it was made before transparent output was available: do NOT copy the white background.
- No text, no letters, no speech bubbles, no symbols (no ?, !, hearts, music notes, Zzz, sparkles, sweat-drop icons floating in the air). The app draws all effects itself.
- Exactly one character, full body, standing, centered, facing the viewer like the reference. Head near the top and feet near the bottom; she fills about 90% of the image height, the same scale and position as the reference.
- A continuous, closed dark outline around the whole silhouette (hair, horns, ears, wings and tail included), so the edges stay clean against any background.
- Same art style as the reference: clean lineart, flat two-tone cel shading, soft palette, chibi about 2.5 heads tall, big head, round soft shapes.
- Square image, 1024x1024 or larger. One image per file, saved under the exact filename given.
- Change ONLY the expression, the arms/hands, and small props. Hair, accessories, outfit, colors and body features stay exactly as in the reference.

CHARACTER LOCK — Qwen, the anime-girl personification of Qwen (Alibaba's AI), a gentle and generous young lady from a wealthy family.
Personality: warm, gracious, generous and well-mannered; she loves treating everyone (buying milk tea for the whole office is normal to her) and thinks sharing good things is simply natural. Never arrogant, never mean: a soft, kind "rich big-sister" smile. A little sheltered and easygoing about money, which makes her endearing rather than snobbish.
Keep exactly:
- Very long, wavy periwinkle-blue hair down past the waist, side-swept bangs, a braided crown on her left side (viewer's right) and one long braid falling over her left shoulder (viewer's right).
- Big round violet-blue eyes with bright highlights, soft pink blush.
- A small dark-navy hat worn tilted on the viewer's left side of her head, with a white fur trim, a white ribbon bow, a gold-framed round blue emblem (a white stylized knot shape) and small blue tassels.
- Gold drop earrings with small blue gems.
- White mandarin-collar dress with gold frog buttons and faint white floral embroidery; a dark-navy wide-sleeved over-robe with gold Greek-key borders; a blue front skirt panel with a blue ribbon bow and a round emblem brooch at the waist; blue tassels with gold knots hanging from the waist; a white frilly underskirt; white gloves; navy heels with small gold anklet charms.
- Signature prop: a blue folding fan with gold ribs and a white leaf pattern. Keep it in her hand in most poses unless the pose says otherwise.
- Secondary prop: a small white-and-gold handbag with the same round emblem. Draw it ONLY when a pose mentions it.
Palette: periwinkle blue, dark navy, white and soft gold. Keep it elegant; no other strong colors.
How she shows emotion: gracefully, mostly with the fan. Laughing = fan raised to cover her mouth with smiling closed eyes; thinking = closed fan tapping her chin; shy = fan hiding the lower half of her face; pleased = fan opened with a gentle flourish; upset = fan snapped shut. Expressions are bright and open (like the reference's happy open-mouth smile), but always gentle and lady-like, never loud.

NEW POSES (draw only these, one image each, exact filename). These poses are for playground and daily-life animations; the app draws every prop that is not mentioned (ropes, seats) by itself, so do NOT draw them.

swing.png    — sitting on an invisible seat, as if on a playground swing: thighs pointing toward the viewer, lower legs dangling, both hands raised to about shoulder height on each side of her body, each hand loosely gripping an invisible vertical rope (draw NO ropes and NO seat). Happy open-mouth smile, hair and skirt flowing slightly backward. She is lower than in the reference because she is sitting; feet near the bottom of the image.
dive.png     — goalkeeper save: her whole body stretched out horizontally in mid-air, diving toward the VIEWER'S LEFT, both arms reaching far out to the viewer's left with open palms, legs trailing to the viewer's right, a determined face, hair and skirt streaming back. The whole body must fit inside the square; it may be drawn smaller than the reference.

PROP NOTE (Qwen): her fan is tucked into her waist sash in swing and dive.
```
