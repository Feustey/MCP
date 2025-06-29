#!/bin/bash

# Script généré automatiquement pour la mise à jour des politiques de frais
# Généré le 2025-06-28 22:12:13

# Canal: ACINQ (1500000 sats)
# Type: major_hub - Direction: out
# Politique actuelle: 20 ppm, 1 sat
# Nouvelle politique: 70 ppm, 600 msats
lncli updatechanpolicy --base_fee_msat 600 --fee_rate_ppm 70 --time_lock_delta 40 --chan_point 781234567890123457:0

# Canal: ACINQ (1500000 sats)
# Type: major_hub - Direction: in
# Politique actuelle: 20 ppm, 1 sat
# Nouvelle politique: 170 ppm, 600 msats
lncli updatechanpolicy --base_fee_msat 600 --fee_rate_ppm 170 --time_lock_delta 40 --chan_point 781234567890123457:0

# Canal: Boltz Exchange (1000000 sats)
# Type: major_hub - Direction: out
# Politique actuelle: 100 ppm, 0 sats
# Nouvelle politique: 70 ppm, 600 msats
lncli updatechanpolicy --base_fee_msat 600 --fee_rate_ppm 70 --time_lock_delta 40 --chan_point 782345678901234568:0

# Canal: Boltz Exchange (1000000 sats)
# Type: major_hub - Direction: in
# Politique actuelle: 100 ppm, 0 sats
# Nouvelle politique: 170 ppm, 600 msats
lncli updatechanpolicy --base_fee_msat 600 --fee_rate_ppm 170 --time_lock_delta 40 --chan_point 782345678901234568:0

# Canal: Bitrefill (800000 sats)
# Type: major_hub - Direction: out
# Politique actuelle: 50 ppm, 1 sat
# Nouvelle politique: 70 ppm, 600 msats
lncli updatechanpolicy --base_fee_msat 600 --fee_rate_ppm 70 --time_lock_delta 40 --chan_point 783456789012345679:0

# Canal: Bitrefill (800000 sats)
# Type: major_hub - Direction: in
# Politique actuelle: 50 ppm, 1 sat
# Nouvelle politique: 170 ppm, 600 msats
lncli updatechanpolicy --base_fee_msat 600 --fee_rate_ppm 170 --time_lock_delta 40 --chan_point 783456789012345679:0

# Canal: Barcelona (650000 sats)
# Type: volume_channel - Direction: out
# Politique actuelle: 150 ppm, 1 sat
# Nouvelle politique: 30 ppm, 500 msats
lncli updatechanpolicy --base_fee_msat 500 --fee_rate_ppm 30 --time_lock_delta 40 --chan_point 784567890123456780:0

# Canal: Barcelona (650000 sats)
# Type: volume_channel - Direction: in
# Politique actuelle: 150 ppm, 1 sat
# Nouvelle politique: 90 ppm, 500 msats
lncli updatechanpolicy --base_fee_msat 500 --fee_rate_ppm 90 --time_lock_delta 40 --chan_point 784567890123456780:0

# Canal: WalletOfSatoshi.com (600000 sats)
# Type: major_hub - Direction: out
# Politique actuelle: 200 ppm, 1 sat
# Nouvelle politique: 70 ppm, 600 msats
lncli updatechanpolicy --base_fee_msat 600 --fee_rate_ppm 70 --time_lock_delta 40 --chan_point 785678901234567891:0

# Canal: WalletOfSatoshi.com (600000 sats)
# Type: major_hub - Direction: in
# Politique actuelle: 200 ppm, 1 sat
# Nouvelle politique: 170 ppm, 600 msats
lncli updatechanpolicy --base_fee_msat 600 --fee_rate_ppm 170 --time_lock_delta 40 --chan_point 785678901234567891:0

# Canal: LN Markets (550000 sats)
# Type: major_hub - Direction: out
# Politique actuelle: 120 ppm, 0 sats
# Nouvelle politique: 70 ppm, 600 msats
lncli updatechanpolicy --base_fee_msat 600 --fee_rate_ppm 70 --time_lock_delta 40 --chan_point 786789012345678902:0

# Canal: LN Markets (550000 sats)
# Type: major_hub - Direction: in
# Politique actuelle: 120 ppm, 0 sats
# Nouvelle politique: 170 ppm, 600 msats
lncli updatechanpolicy --base_fee_msat 600 --fee_rate_ppm 170 --time_lock_delta 40 --chan_point 786789012345678902:0

# Canal: Buda.com (500000 sats)
# Type: volume_channel - Direction: out
# Politique actuelle: 80 ppm, 2 sats
# Nouvelle politique: 30 ppm, 500 msats
lncli updatechanpolicy --base_fee_msat 500 --fee_rate_ppm 30 --time_lock_delta 40 --chan_point 787890123456789013:0

# Canal: Buda.com (500000 sats)
# Type: volume_channel - Direction: in
# Politique actuelle: 80 ppm, 2 sats
# Nouvelle politique: 90 ppm, 500 msats
lncli updatechanpolicy --base_fee_msat 500 --fee_rate_ppm 90 --time_lock_delta 40 --chan_point 787890123456789013:0

# Canal: River Financial (450000 sats)
# Type: major_hub - Direction: out
# Politique actuelle: 180 ppm, 1 sat
# Nouvelle politique: 70 ppm, 600 msats
lncli updatechanpolicy --base_fee_msat 600 --fee_rate_ppm 70 --time_lock_delta 40 --chan_point 788901234567890124:0

# Canal: River Financial (450000 sats)
# Type: major_hub - Direction: in
# Politique actuelle: 180 ppm, 1 sat
# Nouvelle politique: 170 ppm, 600 msats
lncli updatechanpolicy --base_fee_msat 600 --fee_rate_ppm 170 --time_lock_delta 40 --chan_point 788901234567890124:0

# Canal: BlockstreamStore (400000 sats)
# Type: volume_channel - Direction: out
# Politique actuelle: 150 ppm, 1 sat
# Nouvelle politique: 30 ppm, 500 msats
lncli updatechanpolicy --base_fee_msat 500 --fee_rate_ppm 30 --time_lock_delta 40 --chan_point 789012345678901235:0

# Canal: BlockstreamStore (400000 sats)
# Type: volume_channel - Direction: in
# Politique actuelle: 150 ppm, 1 sat
# Nouvelle politique: 90 ppm, 500 msats
lncli updatechanpolicy --base_fee_msat 500 --fee_rate_ppm 90 --time_lock_delta 40 --chan_point 789012345678901235:0

# Canal: Kollider (350000 sats)
# Type: volume_channel - Direction: out
# Politique actuelle: 250 ppm, 0 sats
# Nouvelle politique: 30 ppm, 500 msats
lncli updatechanpolicy --base_fee_msat 500 --fee_rate_ppm 30 --time_lock_delta 40 --chan_point 780123456789012346:0

# Canal: Kollider (350000 sats)
# Type: volume_channel - Direction: in
# Politique actuelle: 250 ppm, 0 sats
# Nouvelle politique: 90 ppm, 500 msats
lncli updatechanpolicy --base_fee_msat 500 --fee_rate_ppm 90 --time_lock_delta 40 --chan_point 780123456789012346:0

# Canal: BestInSlot (243000 sats)
# Type: volume_channel - Direction: out
# Politique actuelle: 300 ppm, 1 sat
# Nouvelle politique: 30 ppm, 500 msats
lncli updatechanpolicy --base_fee_msat 500 --fee_rate_ppm 30 --time_lock_delta 40 --chan_point 781234567890123458:0

# Canal: BestInSlot (243000 sats)
# Type: volume_channel - Direction: in
# Politique actuelle: 300 ppm, 1 sat
# Nouvelle politique: 90 ppm, 500 msats
lncli updatechanpolicy --base_fee_msat 500 --fee_rate_ppm 90 --time_lock_delta 40 --chan_point 781234567890123458:0

# Canal: Breez Mobile (200000 sats)
# Type: volume_channel - Direction: out
# Politique actuelle: 350 ppm, 0 sats
# Nouvelle politique: 30 ppm, 500 msats
lncli updatechanpolicy --base_fee_msat 500 --fee_rate_ppm 30 --time_lock_delta 40 --chan_point 782345678901234569:0

# Canal: Breez Mobile (200000 sats)
# Type: volume_channel - Direction: in
# Politique actuelle: 350 ppm, 0 sats
# Nouvelle politique: 90 ppm, 500 msats
lncli updatechanpolicy --base_fee_msat 500 --fee_rate_ppm 90 --time_lock_delta 40 --chan_point 782345678901234569:0

