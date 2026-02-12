"""
Add medical/mental health disclaimer to all Mental Health Resources pages.
Inserts a disclaimer section before the <footer> tag in each sub-page.
"""
import os
import re

MH_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'MENTALHEALTHRESOURCES')

DISCLAIMER_HTML = '''
    <section class="disclaimer-section" style="max-width:800px;margin:2rem auto;padding:0 1rem;">
      <div style="background:var(--surface-1,#1a1a1a);border:1px solid rgba(255,255,255,0.1);border-radius:0.75rem;padding:2rem;margin-top:2rem;">
        <h3 style="color:var(--pk-500,#ec4899);font-size:1.1rem;margin-bottom:1rem;display:flex;align-items:center;gap:0.5rem;">
          <span style="font-size:1.25rem;">&#9878;</span> Medical &amp; Mental Health Disclaimer
        </h3>
        <div style="color:var(--text-2,#a3a3a3);font-size:0.85rem;line-height:1.7;">
          <p style="margin-bottom:0.75rem;">
            <strong style="color:var(--text-1,#ffffff);">Not a Substitute for Professional Medical Advice.</strong>
            The information provided on this website is for general informational and educational purposes only. It is not intended to be, and should not be interpreted as, medical advice, mental health counseling, diagnosis, or treatment. The content on this site does not replace the relationship between you and your doctor, psychiatrist, psychologist, or other qualified healthcare provider.
          </p>
          <p style="margin-bottom:0.75rem;">
            <strong style="color:var(--text-1,#ffffff);">No Doctor-Patient or Therapist-Client Relationship.</strong>
            Your use of this website does not create a doctor-patient, therapist-client, or any other professional healthcare relationship between you and the operators of this website. We are not a medical provider, mental health clinic, or healthcare facility.
          </p>
          <p style="margin-bottom:0.75rem;">
            <strong style="color:var(--text-1,#ffffff);">Always Seek Professional Advice.</strong>
            If you have or suspect you may have a medical or mental health condition, or if you are experiencing psychological distress, always seek the advice of a qualified healthcare provider. Never disregard professional medical advice or delay seeking it because of information you have read on this website.
          </p>
          <div style="background:linear-gradient(90deg,#dc2626 0%,#991b1b 100%);color:white;padding:1rem;border-radius:0.5rem;margin:1rem 0;">
            <p style="margin:0;font-weight:bold;font-size:0.9rem;">
              &#128680; If you are experiencing a medical or mental health emergency, or if you are having thoughts of suicide or self-harm, seek immediate help:
            </p>
            <ul style="margin:0.75rem 0 0 1.5rem;font-size:0.85rem;">
              <li><strong>Call 911</strong> for immediate emergency assistance</li>
              <li><strong>Call or text 9-8-8</strong> &mdash; Canada Suicide Crisis Helpline (24/7)</li>
              <li><strong>Kids Help Phone:</strong> 1-800-668-6868 or text CONNECT to 686868 (ages 5&ndash;29, 24/7)</li>
              <li><strong>Hope for Wellness Help Line</strong> (Indigenous peoples): 1-855-242-3310 (24/7)</li>
              <li><strong>Crisis Text Line:</strong> Text HOME to 741741 (24/7)</li>
            </ul>
          </div>
          <p style="margin-bottom:0.75rem;">
            <strong style="color:var(--text-1,#ffffff);">Limitation of Liability.</strong>
            While we strive to provide accurate and up-to-date information, we make no representations or warranties of any kind, express or implied, about the completeness, accuracy, reliability, or suitability of the information contained on this website. Any reliance you place on such information is strictly at your own risk. In no event will we be liable for any loss or damage arising from the use of this website or the information provided herein.
          </p>
          <p style="margin:0;font-size:0.8rem;color:var(--text-3,#737373);font-style:italic;">
            Last updated: February 2026
          </p>
        </div>
      </div>
    </section>
'''

# Sub-pages (not index.html) - insert before <footer>
SUB_PAGES = [
    '5-3-1_Social_Fitness.html',
    '5-4-3-2-1_Grounding.html',
    'Anger_Management.html',
    'Breathing_Exercise.html',
    'Color_Therapy_Game.html',
    'Cyclical_Sighing.html',
    'Demographics.html',
    'Gratitude_Journal.html',
    'Identity_Builder.html',
    'Mindfulness_Meditation.html',
    'Online_Resources.html',
    'Panic_Attack_Relief.html',
    'Progressive_Muscle_Relaxation.html',
    'Quick_Coherence.html',
    'Research_Science.html',
    'Sources_References.html',
    'Vagus_Nerve_Reset.html',
]

def update_sub_page(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Skip if disclaimer already added
    if 'Medical &amp; Mental Health Disclaimer' in content or 'disclaimer-section' in content:
        print(f'  SKIP (already has disclaimer): {os.path.basename(filepath)}')
        return False

    # Insert before the first <footer> tag
    footer_match = re.search(r'\n(\s*)<footer', content)
    if footer_match:
        insert_pos = footer_match.start()
        indent = footer_match.group(1)
        content = content[:insert_pos] + '\n' + DISCLAIMER_HTML + '\n' + content[insert_pos:]
    else:
        # Fallback: insert before </body>
        body_match = re.search(r'</body>', content)
        if body_match:
            insert_pos = body_match.start()
            content = content[:insert_pos] + DISCLAIMER_HTML + '\n' + content[insert_pos:]
        else:
            print(f'  ERROR: No footer or body tag found in {os.path.basename(filepath)}')
            return False

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f'  UPDATED: {os.path.basename(filepath)}')
    return True


def main():
    print('Adding medical disclaimer to Mental Health Resources sub-pages...')
    print(f'Directory: {MH_DIR}\n')

    updated = 0
    for page in SUB_PAGES:
        filepath = os.path.join(MH_DIR, page)
        if os.path.exists(filepath):
            if update_sub_page(filepath):
                updated += 1
        else:
            print(f'  NOT FOUND: {page}')

    print(f'\nDone! Updated {updated}/{len(SUB_PAGES)} sub-pages.')


if __name__ == '__main__':
    main()
