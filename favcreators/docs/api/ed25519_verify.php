<?php
/**
 * Pure PHP Ed25519 signature verification
 * Based on TweetNaCl.js port - minimal implementation for Discord verification
 * PHP 5.2 compatible
 */

class Ed25519Verify {
    
    // Field element operations for Ed25519
    private static $D = null;
    private static $D2 = null;
    private static $I = null;
    private static $gf0 = null;
    private static $gf1 = null;
    private static $X = null;
    private static $Y = null;
    
    private static function init() {
        if (self::$gf0 !== null) return;
        
        self::$gf0 = array_fill(0, 16, 0);
        self::$gf1 = array_fill(0, 16, 0);
        self::$gf1[0] = 1;
        
        self::$D = array(
            0x78a3, 0x1359, 0x4dca, 0x75eb, 0xd8ab, 0x4141, 0x0a4d, 0x0070,
            0xe898, 0x7779, 0x4079, 0x8cc7, 0xfe73, 0x2b6f, 0x6cee, 0x5203
        );
        
        self::$D2 = array(
            0xf159, 0x26b2, 0x9b94, 0xebd6, 0xb156, 0x8283, 0x149a, 0x00e0,
            0xd130, 0xeef3, 0x80f2, 0x198e, 0xfce7, 0x56df, 0xd9dc, 0x2406
        );
        
        self::$I = array(
            0xa0b0, 0x4a0e, 0x1b27, 0xc4ee, 0xe478, 0xad2f, 0x1806, 0x2f43,
            0xd7a7, 0x3dfb, 0x0099, 0x2b4d, 0xdf0b, 0x4fc1, 0x2480, 0x2b83
        );
        
        self::$X = array(
            0xd51a, 0x8f25, 0x2d60, 0xc956, 0xa7b2, 0x9525, 0xc760, 0x692c,
            0xdc5c, 0xfdd6, 0xe231, 0xc0a4, 0x53fe, 0xcd6e, 0x36d3, 0x2169
        );
        
        self::$Y = array(
            0x6658, 0x6666, 0x6666, 0x6666, 0x6666, 0x6666, 0x6666, 0x6666,
            0x6666, 0x6666, 0x6666, 0x6666, 0x6666, 0x6666, 0x6666, 0x6666
        );
    }
    
    public static function verify($signature, $message, $publicKey) {
        self::init();
        
        if (strlen($signature) !== 64) return false;
        if (strlen($publicKey) !== 32) return false;
        
        $sig = array_values(unpack('C*', $signature));
        $pk = array_values(unpack('C*', $publicKey));
        $m = array_values(unpack('C*', $message));
        
        // Check s < L
        if (!self::checkLt($sig, 32)) return false;
        
        // Unpack public key to point
        $A = self::unpackPoint($pk);
        if ($A === false) return false;
        
        // Build hash input: R || A || M
        $sm = array_merge(array_slice($sig, 0, 32), $pk, $m);
        
        // Hash to get h
        $h = self::sha512($sm);
        $h = self::reduce($h);
        
        // Compute [s]B - [h]A
        $sB = self::scalarMult(self::getBasePoint(), array_slice($sig, 32, 32));
        $hA = self::scalarMult($A, $h);
        $hA = self::negatePoint($hA);
        $check = self::addPoints($sB, $hA);
        
        // Pack result and compare to R
        $checkPacked = self::packPoint($check);
        
        return self::constTimeCompare($checkPacked, array_slice($sig, 0, 32));
    }
    
    private static function sha512($data) {
        $str = '';
        foreach ($data as $byte) {
            $str .= chr($byte);
        }
        $hash = hash('sha512', $str, true);
        return array_values(unpack('C*', $hash));
    }
    
    private static function reduce($h) {
        $x = array_fill(0, 64, 0);
        for ($i = 0; $i < 64; $i++) {
            $x[$i] = $h[$i];
        }
        
        $L = array(
            0xed, 0xd3, 0xf5, 0x5c, 0x1a, 0x63, 0x12, 0x58,
            0xd6, 0x9c, 0xf7, 0xa2, 0xde, 0xf9, 0xde, 0x14,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x10
        );
        
        for ($i = 63; $i >= 32; $i--) {
            $carry = 0;
            for ($j = $i - 32; $j < $i - 12; $j++) {
                $x[$j] += $carry - 16 * $x[$i] * $L[$j - ($i - 32)];
                $carry = ($x[$j] + 128) >> 8;
                $x[$j] -= $carry * 256;
            }
            $x[$i - 12] += $carry;
            $x[$i] = 0;
        }
        
        $carry = 0;
        for ($j = 0; $j < 32; $j++) {
            $x[$j] += $carry - ($x[31] >> 4) * $L[$j];
            $carry = $x[$j] >> 8;
            $x[$j] &= 255;
        }
        
        for ($j = 0; $j < 32; $j++) {
            $x[$j] -= $carry * $L[$j];
        }
        
        $r = array();
        for ($i = 0; $i < 32; $i++) {
            $x[$i + 1] += $x[$i] >> 8;
            $r[$i] = $x[$i] & 255;
        }
        
        return $r;
    }
    
    private static function checkLt($s, $offset) {
        $L = array(
            0xed, 0xd3, 0xf5, 0x5c, 0x1a, 0x63, 0x12, 0x58,
            0xd6, 0x9c, 0xf7, 0xa2, 0xde, 0xf9, 0xde, 0x14,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x10
        );
        
        $c = 0;
        for ($i = 31; $i >= 0; $i--) {
            $a = $s[$offset + $i];
            $b = $L[$i];
            if ($a < $b) $c = 1;
            if ($a > $b) $c = 0;
        }
        return $c == 1;
    }
    
    private static function constTimeCompare($a, $b) {
        if (count($a) !== count($b)) return false;
        $d = 0;
        for ($i = 0; $i < count($a); $i++) {
            $d |= $a[$i] ^ $b[$i];
        }
        return $d === 0;
    }
    
    private static function getBasePoint() {
        self::init();
        return array(self::$X, self::$Y, self::$gf1, self::gfMul(self::$X, self::$Y));
    }
    
    private static function gfMul($a, $b) {
        $t = array_fill(0, 31, 0);
        for ($i = 0; $i < 16; $i++) {
            for ($j = 0; $j < 16; $j++) {
                $t[$i + $j] += $a[$i] * $b[$j];
            }
        }
        for ($i = 0; $i < 15; $i++) {
            $t[$i] += 38 * $t[$i + 16];
        }
        $o = array_fill(0, 16, 0);
        for ($i = 0; $i < 16; $i++) {
            $o[$i] = $t[$i];
        }
        self::car25519($o);
        self::car25519($o);
        return $o;
    }
    
    private static function car25519(&$o) {
        $c = 0;
        for ($i = 0; $i < 16; $i++) {
            $o[$i] += 65536;
            $c = floor($o[$i] / 65536);
            $o[($i + 1) % 16] += $c - 1 + 37 * ($c - 1) * (($i == 15) ? 1 : 0);
            $o[$i] -= $c * 65536;
        }
    }
    
    private static function unpackPoint($p) {
        self::init();
        
        $r = array(self::$gf0, self::$gf0, self::$gf0, self::$gf0);
        for ($i = 0; $i < 4; $i++) {
            $r[$i] = array_merge(array(), $r[$i]);
        }
        
        // y coordinate
        for ($i = 0; $i < 16; $i++) {
            $r[1][$i] = $p[2 * $i] + ($p[2 * $i + 1] << 8);
        }
        
        // z = 1
        $r[2] = array_merge(array(), self::$gf1);
        
        // x^2 = (y^2 - 1) / (d*y^2 + 1)
        $y2 = self::gfMul($r[1], $r[1]);
        $dy2 = self::gfMul(self::$D, $y2);
        $y2m1 = self::gfSub($y2, self::$gf1);
        $dy2p1 = self::gfAdd($dy2, self::$gf1);
        $dy2p1inv = self::gfInv($dy2p1);
        $x2 = self::gfMul($y2m1, $dy2p1inv);
        
        $r[0] = self::gfSqrt($x2);
        if ($r[0] === false) return false;
        
        // Check sign
        if (($r[0][0] & 1) !== (($p[31] >> 7) & 1)) {
            $r[0] = self::gfNeg($r[0]);
        }
        
        $r[3] = self::gfMul($r[0], $r[1]);
        
        return $r;
    }
    
    private static function gfAdd($a, $b) {
        $o = array();
        for ($i = 0; $i < 16; $i++) {
            $o[$i] = $a[$i] + $b[$i];
        }
        return $o;
    }
    
    private static function gfSub($a, $b) {
        $o = array();
        for ($i = 0; $i < 16; $i++) {
            $o[$i] = $a[$i] - $b[$i];
        }
        return $o;
    }
    
    private static function gfNeg($a) {
        $o = array();
        for ($i = 0; $i < 16; $i++) {
            $o[$i] = -$a[$i];
        }
        return $o;
    }
    
    private static function gfInv($a) {
        $c = array_merge(array(), $a);
        for ($i = 253; $i >= 0; $i--) {
            $c = self::gfMul($c, $c);
            if ($i != 2 && $i != 4) {
                $c = self::gfMul($c, $a);
            }
        }
        return $c;
    }
    
    private static function gfSqrt($a) {
        self::init();
        
        // p = 2^255 - 19, compute a^((p+3)/8)
        $x = self::gfPow($a, array(
            0xfb, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
            0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
            0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
            0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x0f
        ));
        
        // Check if x^2 = a
        $check = self::gfMul($x, $x);
        if (!self::gfEq($check, $a)) {
            // Try x * sqrt(-1)
            $x = self::gfMul($x, self::$I);
            $check = self::gfMul($x, $x);
            if (!self::gfEq($check, $a)) {
                return false;
            }
        }
        
        return $x;
    }
    
    private static function gfPow($a, $exp) {
        $r = array_merge(array(), self::$gf1);
        $t = array_merge(array(), $a);
        
        for ($i = 0; $i < 256; $i++) {
            $byte = $exp[intval($i / 8)];
            $bit = ($byte >> ($i % 8)) & 1;
            if ($bit) {
                $r = self::gfMul($r, $t);
            }
            $t = self::gfMul($t, $t);
        }
        
        return $r;
    }
    
    private static function gfEq($a, $b) {
        $pa = self::gfPack($a);
        $pb = self::gfPack($b);
        return self::constTimeCompare($pa, $pb);
    }
    
    private static function gfPack($n) {
        $t = array_merge(array(), $n);
        self::car25519($t);
        self::car25519($t);
        self::car25519($t);
        
        // Reduce mod 2^255-19
        $m = array_fill(0, 16, 0);
        for ($j = 0; $j < 2; $j++) {
            $m[0] = $t[0] - 0xffed;
            for ($i = 1; $i < 15; $i++) {
                $m[$i] = $t[$i] - 0xffff - (($m[$i - 1] >> 16) & 1);
                $m[$i - 1] &= 0xffff;
            }
            $m[15] = $t[15] - 0x7fff - (($m[14] >> 16) & 1);
            $b = ($m[15] >> 16) & 1;
            $m[14] &= 0xffff;
            for ($i = 0; $i < 16; $i++) {
                $t[$i] = $b ? $t[$i] : $m[$i];
            }
        }
        
        $o = array();
        for ($i = 0; $i < 16; $i++) {
            $o[2 * $i] = $t[$i] & 0xff;
            $o[2 * $i + 1] = ($t[$i] >> 8) & 0xff;
        }
        return $o;
    }
    
    private static function scalarMult($p, $s) {
        self::init();
        $q = array(self::$gf0, self::$gf1, self::$gf1, self::$gf0);
        for ($i = 0; $i < 4; $i++) {
            $q[$i] = array_merge(array(), $q[$i]);
        }
        
        for ($i = 255; $i >= 0; $i--) {
            $byte = $s[intval($i / 8)];
            $bit = ($byte >> ($i % 8)) & 1;
            if ($bit) {
                $q = self::addPoints($q, $p);
            }
            $p = self::addPoints($p, $p);
        }
        
        return $q;
    }
    
    private static function addPoints($p, $q) {
        self::init();
        
        $a = self::gfMul(self::gfSub($p[1], $p[0]), self::gfSub($q[1], $q[0]));
        $b = self::gfMul(self::gfAdd($p[1], $p[0]), self::gfAdd($q[1], $q[0]));
        $c = self::gfMul(self::gfMul($p[3], $q[3]), self::$D2);
        $c = self::gfAdd($c, $c);
        $d = self::gfMul($p[2], $q[2]);
        $d = self::gfAdd($d, $d);
        $e = self::gfSub($b, $a);
        $f = self::gfSub($d, $c);
        $g = self::gfAdd($d, $c);
        $h = self::gfAdd($b, $a);
        
        return array(
            self::gfMul($e, $f),
            self::gfMul($h, $g),
            self::gfMul($g, $f),
            self::gfMul($e, $h)
        );
    }
    
    private static function negatePoint($p) {
        return array(
            self::gfNeg($p[0]),
            array_merge(array(), $p[1]),
            array_merge(array(), $p[2]),
            self::gfNeg($p[3])
        );
    }
    
    private static function packPoint($p) {
        $zi = self::gfInv($p[2]);
        $tx = self::gfMul($p[0], $zi);
        $ty = self::gfMul($p[1], $zi);
        $r = self::gfPack($ty);
        $txp = self::gfPack($tx);
        $r[31] ^= ($txp[0] & 1) << 7;
        return $r;
    }
}

/**
 * Convenience function for Discord signature verification
 */
function verify_discord_request($body, $signature_hex, $timestamp, $public_key_hex) {
    if (empty($signature_hex) || empty($timestamp) || empty($public_key_hex)) {
        return false;
    }
    
    $signature = @pack('H*', $signature_hex);
    $public_key = @pack('H*', $public_key_hex);
    
    if ($signature === false || strlen($signature) !== 64) {
        return false;
    }
    if ($public_key === false || strlen($public_key) !== 32) {
        return false;
    }
    
    $message = $timestamp . $body;
    
    return Ed25519Verify::verify($signature, $message, $public_key);
}
