"""Fix app.js: show results instantly, fetch OSRM in background."""
import re

path = r'c:\Users\Walid\Desktop\collecte_agadir\webapp\static\js\app.js'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# We need to replace everything between "state.results = data;" and the closing "}" of runOptimization
# Find the target area using a regex approach
# Match from "state.results = data;" up to the closing of runOptimization function

old_pattern = r'        state\.results = data;\s*\n\s*// Fetch OSRM road-geometry.*?finally \{[^}]*\}\s*\n\s*\}'

new_code = """        state.results = data;
        const routes = data.vrp?.routes || [];

        // INSTANT: show results with straight-line routes
        drawRoutes(data);
        showResults(data);
        showToast('\\u2705 Optimisation termin\\u00e9e !', 'success');
        if (btn) { btn.disabled = false; btn.innerHTML = '\\ud83d\\ude80 Lancer l\\'Optimisation'; }

        // BACKGROUND: upgrade to real OSRM road routes (non-blocking)
        fetchOSRMRoutesInBackground(routes, data);

    } catch (e) {
        showToast(`Erreur: ${e.message}`, 'error');
        if (btn) { btn.disabled = false; btn.innerHTML = '\\ud83d\\ude80 Lancer l\\'Optimisation'; }
    }
}

async function fetchOSRMRoutesInBackground(routes, data) {
    try {
        const osrmResults = [];
        for (let i = 0; i < routes.length; i++) {
            const wp = routes[i].coordinates || [];
            if (wp.length >= 2) {
                osrmResults.push(await fetchFullOSRMRoute(wp));
                if (i < routes.length - 1) await new Promise(r => setTimeout(r, 300));
            } else {
                osrmResults.push(wp);
            }
        }
        state.osrmRoutes = osrmResults;
        routes.forEach((route, i) => { route.osrm_coordinates = osrmResults[i]; });
        drawRoutes(data);
        showToast('\\ud83d\\uddfa\\ufe0f Routes routi\\u00e8res mises \\u00e0 jour', 'success');
    } catch (e) {
        console.warn('Background OSRM fetch failed:', e);
    }
}"""

match = re.search(old_pattern, content, re.DOTALL)
if match:
    # Preserve the line ending style of the file
    eol = '\r\n' if '\r\n' in content else '\n'
    new_code_eol = new_code.replace('\n', eol)
    content = content[:match.start()] + new_code_eol + content[match.end():]
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: app.js updated')
else:
    print('ERROR: Pattern not found')
    # Debug: show lines around state.results
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'state.results = data' in line:
            print(f'Found at line {i+1}: {repr(line)}')
        if 'finally' in line and i > 480:
            print(f'Finally at line {i+1}: {repr(line)}')
